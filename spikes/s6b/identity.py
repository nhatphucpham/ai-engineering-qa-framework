"""In-process identity persistence experiment, no HTTP/OS credentials/service broker."""
from preflight_b import ROOT,DEPS,inventory
import sys
if not inventory()['ready']:raise RuntimeError('E_PREREQUISITES')
sys.path.insert(0,str(DEPS))
from argon2 import PasswordHasher,profiles
from argon2.exceptions import VerificationError,InvalidHashError
import contextlib,hashlib,re,secrets,uuid
from types import MappingProxyType
from pathlib import Path
sys.path.insert(0,str(ROOT/'spikes/s2'))
from local import connect
sys.path.insert(0,str(ROOT/'.cache/s2/deps'))
from psycopg import sql
from psycopg.rows import dict_row
from psycopg.types.json import Jsonb

PH=PasswordHasher.from_parameters(profiles.RFC_9106_LOW_MEMORY)
READ={'read','report','source','export','stream'}
ALLOWED={'Viewer':READ,'Runner':READ|{'start','cancel'},'Owner':READ|{'start','cancel','config'},'Admin':READ|{'start','cancel','config'}}

class Denied(Exception):
    def __init__(self,code='E_AUTH'):self.code=code;super().__init__(code)

def name(value):
    if not isinstance(value,str) or not re.fullmatch(r'[A-Za-z][A-Za-z0-9_-]{0,63}',value):raise Denied('E_DENIED')

def password(value):
    if not isinstance(value,str) or not 16<=len(value.encode('utf-8'))<=1024:raise Denied()

def digest(token,kind):
    if not isinstance(token,str) or not re.fullmatch(re.escape(kind)+r'\.[A-Za-z0-9_-]{43}',token):raise Denied()
    return hashlib.sha256(token.encode()).hexdigest()

def positive(value):
    if type(value) is not int or value<1:raise Denied('E_DENIED')


class _Store:
    def __init__(self,schema,create=False):
        if not re.fullmatch(r'id_[a-f0-9]{32}',schema):raise Denied('E_SCHEMA')
        self.conn=connect();self.conn.row_factory=dict_row;self.schema=schema
        if create:
            with self.conn.transaction():
                self.conn.execute(sql.SQL('CREATE SCHEMA {}').format(sql.Identifier(schema)))
                self.conn.execute(sql.SQL('SET search_path TO {},public').format(sql.Identifier(schema)))
                self.conn.execute((Path(__file__).parent/'schema.sql').read_text())
                self.conn.execute('INSERT INTO control(id,dummy_hash) VALUES(1,%s)',(PH.hash(secrets.token_urlsafe(32)),))
        else:self.conn.execute(sql.SQL('SET search_path TO {},public').format(sql.Identifier(schema)))
        if self.conn.execute('SELECT version FROM model_identity').fetchone()!={'version':'s6b-1.0.0'}:raise Denied('E_SCHEMA')
    def close(self):self.conn.close()
    def audit(self,user,op):self.conn.execute('INSERT INTO audit(user_id,operation) VALUES(%s,%s)',(user,op))
    def principal(self,access,restricted=False):
        row=self.conn.execute('''SELECT a.id,a.admin,a.must_change,a.epoch,f.id AS family,
            t.expires AS access_expires,f.expires AS family_expires FROM access_tokens t JOIN families f ON f.id=t.family
            JOIN accounts a ON a.id=f.user_id WHERE t.digest=%s AND t.expires>clock_timestamp() AND f.expires>clock_timestamp()
            AND NOT f.revoked AND a.enabled AND a.epoch=f.epoch AND t.generation=f.generation''',(digest(access,'a'),)).fetchone()
        if row is None or row['must_change'] and not restricted:raise Denied()
        return row
    @contextlib.contextmanager
    def tx(self,access=None,restricted=False,before_finish=lambda:None):
        with self.conn.transaction():
            self.conn.execute('SELECT * FROM control WHERE id=1 FOR UPDATE')
            actor=self.principal(access,restricted) if access is not None else None
            yield actor
            if actor is not None:
                before_finish()
                # All credential/role mutations share the held mutex. Own logout/reset may
                # intentionally revoke this actor, so recheck its captured DB expiries only.
                if self.conn.execute('''UPDATE control SET serial=serial+1 WHERE id=1
                    AND %s>clock_timestamp() AND %s>clock_timestamp() RETURNING id''',
                    (actor['access_expires'],actor['family_expires'])).fetchone() is None:raise Denied()
    def bootstrap(self,user,pw):
        name(user);password(pw);encoded=PH.hash(pw)
        with self.tx():
            if self.conn.execute('SELECT bootstrapped FROM control').fetchone()['bootstrapped'] or self.conn.execute('SELECT 1 FROM accounts LIMIT 1').fetchone():raise Denied('E_DENIED')
            self.conn.execute('INSERT INTO accounts(id,password_hash,admin) VALUES(%s,%s,true)',(user,encoded))
            self.conn.execute('UPDATE control SET bootstrapped=true WHERE id=1');self.audit(user,'bootstrap')
    def _issue(self,user,access_ms=60000,refresh_ms=600000,family=None):
        for value in (access_ms,refresh_ms):
            if type(value) is not int or not 50<=value<=1800000:raise Denied()
        if family is None:
            family=uuid.uuid4().hex
            epoch=self.conn.execute('SELECT epoch FROM accounts WHERE id=%s',(user,)).fetchone()['epoch']
            self.conn.execute("INSERT INTO families VALUES(%s,%s,%s,1,false,clock_timestamp()+interval '1 hour')",(family,user,epoch))
        f=self.conn.execute('SELECT * FROM families WHERE id=%s',(family,)).fetchone()
        a='a.'+secrets.token_urlsafe(32);r='r.'+secrets.token_urlsafe(32)
        self.conn.execute("INSERT INTO access_tokens VALUES(%s,%s,%s,LEAST(%s,clock_timestamp()+(%s*interval '1 millisecond')))",
                          (digest(a,'a'),family,f['generation'],f['expires'],access_ms))
        self.conn.execute("INSERT INTO refresh_tokens VALUES(%s,%s,%s,LEAST(%s,clock_timestamp()+(%s*interval '1 millisecond')),false)",
                          (digest(r,'r'),family,f['generation'],f['expires'],refresh_ms))
        return {'access':a,'refresh':r}
    def login(self,user,pw,access_ms=60000,refresh_ms=600000):
        # Shape limits bound expensive work; no password normalization/truncation.
        if not isinstance(user,str) or not re.fullmatch(r'[A-Za-z][A-Za-z0-9_-]{0,63}',user):raise Denied()
        password(pw);pair=None
        with self.tx():
            control=self.conn.execute('SELECT *,clock_timestamp() AS now FROM control').fetchone();now=control['now']
            bucket=hashlib.sha256(user.encode()).hexdigest()
            self.conn.execute('''INSERT INTO login_buckets VALUES(%s,0,clock_timestamp()) ON CONFLICT DO NOTHING''',(bucket,))
            self.conn.execute("UPDATE control SET login_count=0,login_window=clock_timestamp() WHERE id=1 AND login_window<clock_timestamp()-interval '1 second'")
            self.conn.execute("UPDATE login_buckets SET attempts=0,window_start=clock_timestamp() WHERE bucket=%s AND window_start<clock_timestamp()-interval '1 second'",(bucket,))
            global_count=self.conn.execute('SELECT login_count FROM control').fetchone()['login_count']
            count=self.conn.execute('SELECT attempts FROM login_buckets WHERE bucket=%s',(bucket,)).fetchone()['attempts']
            if global_count<30 and count<3:
                self.conn.execute('UPDATE control SET login_count=login_count+1 WHERE id=1')
                self.conn.execute('UPDATE login_buckets SET attempts=attempts+1 WHERE bucket=%s',(bucket,))
                row=self.conn.execute('SELECT * FROM accounts WHERE id=%s',(user,)).fetchone()
                encoded=row['password_hash'] if row is not None and row['enabled'] else control['dummy_hash']
                try:valid=PH.verify(encoded,pw)
                except (VerificationError,InvalidHashError):valid=False
                if valid and row is not None and row['enabled']:
                    pair=self._issue(user,access_ms,refresh_ms);self.audit(user,'login')
            if pair is None:self.audit(None,'login_denied')
        if pair is None:raise Denied()
        return pair
    def refresh(self,token,access_ms=60000,refresh_ms=600000,before_write=lambda:None):
        token_digest=digest(token,'r');pair=None
        with self.tx():
            row=self.conn.execute('''SELECT r.*,f.user_id,f.revoked,f.generation AS current_generation,f.epoch AS family_epoch,
                a.epoch,a.enabled,a.must_change FROM refresh_tokens r JOIN families f ON f.id=r.family
                JOIN accounts a ON a.id=f.user_id WHERE r.digest=%s''',(token_digest,)).fetchone()
            if row is not None:
                if row['used']:
                    self.conn.execute('UPDATE families SET revoked=true WHERE id=%s',(row['family'],));self.audit(row['user_id'],'refresh_reuse')
                elif not row['revoked'] and row['enabled'] and not row['must_change'] and row['epoch']==row['family_epoch'] and row['generation']==row['current_generation']:
                    before_write()
                    used=self.conn.execute('''UPDATE refresh_tokens SET used=true WHERE digest=%s AND NOT used AND expires>clock_timestamp()
                        AND EXISTS(SELECT 1 FROM families WHERE id=%s AND expires>clock_timestamp()) RETURNING digest''',(token_digest,row['family'])).fetchone()
                    if used:
                        self.conn.execute('UPDATE families SET generation=generation+1 WHERE id=%s',(row['family'],))
                        pair=self._issue(row['user_id'],access_ms,refresh_ms,row['family']);self.audit(row['user_id'],'refresh')
            if pair is None:self.audit(None,'refresh_denied')
        if pair is None:raise Denied()
        return pair
    def logout(self,access):
        with self.tx(access,restricted=True) as actor:
            self.conn.execute('UPDATE families SET revoked=true WHERE id=%s',(actor['family'],));self.audit(actor['id'],'logout')
    def change_password(self,access,old,new):
        password(old);password(new)
        if old==new:raise Denied()
        with self.tx(access,restricted=True) as actor:
            row=self.conn.execute('SELECT password_hash FROM accounts WHERE id=%s',(actor['id'],)).fetchone()
            try:PH.verify(row['password_hash'],old)
            except (VerificationError,InvalidHashError):raise Denied() from None
            encoded=PH.hash(new)
            self.conn.execute('UPDATE accounts SET password_hash=%s,must_change=false,epoch=epoch+1 WHERE id=%s',(encoded,actor['id']))
            self.conn.execute('UPDATE families SET revoked=true WHERE user_id=%s',(actor['id'],));self.audit(actor['id'],'password_change')
    @staticmethod
    def admin(actor):
        if not actor['admin']:raise Denied('E_DENIED')
    def create_account(self,access,user,pw):
        name(user);password(pw)
        with self.tx(access) as actor:
            self.admin(actor);encoded=PH.hash(pw)
            self.conn.execute('INSERT INTO accounts(id,password_hash) VALUES(%s,%s)',(user,encoded));self.audit(actor['id'],'create_account')
    def reset_password(self,access,user,new):
        name(user);password(new)
        with self.tx(access) as actor:
            self.admin(actor);encoded=PH.hash(new)
            if self.conn.execute('UPDATE accounts SET password_hash=%s,must_change=true,epoch=epoch+1 WHERE id=%s RETURNING id',(encoded,user)).fetchone() is None:raise Denied('E_DENIED')
            self.conn.execute('UPDATE families SET revoked=true WHERE user_id=%s',(user,));self.audit(actor['id'],'reset_password')
    def account_flag(self,access,user,field,value):
        name(user)
        if field not in ('admin','enabled') or type(value) is not bool:raise Denied('E_DENIED')
        with self.tx(access) as actor:
            self.admin(actor);target=self.conn.execute('SELECT * FROM accounts WHERE id=%s',(user,)).fetchone()
            if target is None:raise Denied('E_DENIED')
            if target['admin'] and target['enabled'] and not value:
                if self.conn.execute('SELECT count(*) AS n FROM accounts WHERE admin AND enabled').fetchone()['n']<=1:raise Denied('E_DENIED')
            self.conn.execute(sql.SQL('UPDATE accounts SET {}=%s,epoch=epoch+1 WHERE id=%s').format(sql.Identifier(field)),(value,user))
            self.conn.execute('UPDATE families SET revoked=true WHERE user_id=%s',(user,));self.audit(actor['id'],'account_flag')
    def create_project(self,access,project,owner):
        name(project);name(owner)
        with self.tx(access) as actor:
            self.admin(actor)
            if not self.conn.execute('SELECT 1 FROM accounts WHERE id=%s AND enabled',(owner,)).fetchone():raise Denied('E_DENIED')
            self.conn.execute('INSERT INTO projects(id) VALUES(%s)',(project,))
            self.conn.execute("INSERT INTO members VALUES(%s,%s,'Owner')",(project,owner));self.audit(actor['id'],'create_project')
    def role(self,actor,project):
        name(project)
        if not self.conn.execute('SELECT 1 FROM projects WHERE id=%s AND enabled',(project,)).fetchone():raise Denied('E_DENIED')
        if actor['admin']:return 'Admin'
        row=self.conn.execute('SELECT role FROM members WHERE project=%s AND user_id=%s',(project,actor['id'])).fetchone()
        if row is None:raise Denied('E_DENIED')
        return row['role']
    def membership(self,access,project,target,role):
        name(target)
        if role not in ('Owner','Runner','Viewer',None):raise Denied('E_DENIED')
        with self.tx(access) as actor:
            current=self.role(actor,project)
            if current not in ('Admin','Owner') or role=='Owner' and current!='Admin':raise Denied('E_DENIED')
            target_row=self.conn.execute('SELECT * FROM accounts WHERE id=%s AND enabled',(target,)).fetchone()
            if target_row is None:raise Denied('E_DENIED')
            existing=self.conn.execute('SELECT role FROM members WHERE project=%s AND user_id=%s',(project,target)).fetchone()
            if existing and existing['role']=='Owner' and role!='Owner':raise Denied('E_DENIED')
            if role=='Owner':self.conn.execute("UPDATE members SET role='Viewer' WHERE project=%s AND role='Owner'",(project,))
            if role is None:self.conn.execute('DELETE FROM members WHERE project=%s AND user_id=%s',(project,target))
            else:self.conn.execute('INSERT INTO members VALUES(%s,%s,%s) ON CONFLICT(project,user_id) DO UPDATE SET role=EXCLUDED.role',(project,target,role))
            self.audit(actor['id'],'membership')
    def project_enabled(self,access,project,enabled):
        if type(enabled) is not bool:raise Denied('E_DENIED')
        with self.tx(access) as actor:
            self.admin(actor)
            if not self.conn.execute('UPDATE projects SET enabled=%s WHERE id=%s RETURNING id',(enabled,project)).fetchone():raise Denied('E_DENIED')
            self.audit(actor['id'],'project_enabled')
    def issue_grant(self,access,project,actions):
        if not isinstance(actions,list) or not actions or not all(isinstance(a,str) for a in actions) or len(actions)!=len(set(actions)):raise Denied('E_DENIED')
        with self.tx(access) as actor:
            role=self.role(actor,project)
            if not set(actions)<=ALLOWED[role]:raise Denied('E_DENIED')
            grant=uuid.uuid4().hex
            self.conn.execute('INSERT INTO grants VALUES(%s,%s,%s,%s,%s)',(grant,actor['id'],project,actor['epoch'],Jsonb(actions)))
            return grant
    def authorize(self,actor,project,action,grant):
        role=self.role(actor,project)
        row=self.conn.execute('SELECT * FROM grants WHERE id=%s',(grant,)).fetchone()
        if (action not in ALLOWED[role] or row is None or (row['user_id'],row['project'],row['epoch'])!=(actor['id'],project,actor['epoch'])
            or action not in row['actions']):raise Denied('E_DENIED')
        return role
    def check(self,access,project,action,grant,**claims):
        if claims:raise Denied('E_DENIED')
        with self.tx(access) as actor:return {'user':actor['id'],'role':self.authorize(actor,project,action,grant)}
    def start_run(self,access,project,run_id,grant,before_finish=lambda:None):
        name(run_id)
        with self.tx(access,before_finish=before_finish) as actor:
            self.authorize(actor,project,'start',grant)
            self.conn.execute("INSERT INTO qa_runs(id,project,initiator,state) VALUES(%s,%s,%s,'queued')",(run_id,project,actor['id']))
    def cancel_run(self,access,run_id,grant,expected_version=1):
        positive(expected_version)
        with self.tx(access) as actor:
            row=self.conn.execute('SELECT * FROM qa_runs WHERE id=%s',(run_id,)).fetchone()
            if row is None:raise Denied('E_DENIED')
            role=self.authorize(actor,row['project'],'cancel',grant)
            if role=='Runner' and row['initiator']!=actor['id']:raise Denied('E_DENIED')
            if not self.conn.execute("UPDATE qa_runs SET state='cancelled',version=version+1 WHERE id=%s AND version=%s AND state='queued' RETURNING id",(run_id,expected_version)).fetchone():raise Denied('E_DENIED')


class Identity:
    """Sole untrusted request facade. No dynamic backend method/SQL/bootstrap access.

    Python host code and introspection are trusted; this is not a process sandbox.
    """
    __slots__=('__store',)
    ROUTES=MappingProxyType({'login':'login','refresh':'refresh','logout':'logout','password_change':'change_password',
        'account_create':'create_account','account_reset':'reset_password','account_flag':'account_flag',
        'project_create':'create_project','membership':'membership','project_enabled':'project_enabled',
        'grant':'issue_grant','check':'check','run_start':'start_run','run_cancel':'cancel_run'})
    FIELDS={'login':{'user','pw'},'refresh':{'token'},'logout':{'access'},'password_change':{'access','old','new'},
        'account_create':{'access','user','pw'},'account_reset':{'access','user','new'},'account_flag':{'access','user','field','value'},
        'project_create':{'access','project','owner'},'membership':{'access','project','target','role'},
        'project_enabled':{'access','project','enabled'},'grant':{'access','project','actions'},
        'check':{'access','project','action','grant'},'run_start':{'access','project','run_id','grant'},
        'run_cancel':{'access','run_id','grant','expected_version'}}
    def __init__(self,schema):self.__store=_Store(schema)
    def dispatch(self,operation,**body):
        if not isinstance(operation,str) or operation not in self.ROUTES or not set(body)<=self.FIELDS[operation]:raise Denied('E_DENIED')
        try:return getattr(self.__store,self.ROUTES[operation])(**body)
        except TypeError:raise Denied('E_DENIED') from None
    def close(self):self.__store.close()
