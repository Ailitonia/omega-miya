from sqlalchemy import Sequence, ForeignKey
from sqlalchemy import Column, Integer, BigInteger, String, DateTime
from sqlalchemy.orm import relationship
from sqlalchemy.ext.declarative import declarative_base

# 创建数据表基类
Base = declarative_base()


# 成员表
class User(Base):
    __tablename__ = 'users'
    __table_args__ = {'mysql_engine': 'InnoDB', 'mysql_charset': 'utf8mb4'}

    # 表结构
    id = Column(Integer, Sequence('users_id_seq'), primary_key=True, nullable=False, index=True, unique=True)
    qq = Column(BigInteger, nullable=False, index=True, unique=True, comment='QQ号')
    nickname = Column(String(64), nullable=False, comment='昵称')
    aliasname = Column(String(64), nullable=True, comment='自定义名称')
    created_at = Column(DateTime, nullable=True)
    updated_at = Column(DateTime, nullable=True)

    # 声明外键联系
    has_skills = relationship('UserSkill', back_populates='user_skill',
                              cascade="all, delete", passive_deletes=True)
    in_which_groups = relationship('UserGroup', back_populates='user_groups',
                                   cascade="all, delete", passive_deletes=True)
    vocation = relationship('Vocation', back_populates='vocation_for_user', uselist=False,
                            cascade="all, delete", passive_deletes=True)
    user_auth = relationship('AuthUser', back_populates='auth_for_user', uselist=False,
                             cascade="all, delete", passive_deletes=True)

    def __init__(self, qq, nickname, aliasname=None, created_at=None, updated_at=None):
        self.qq = qq
        self.nickname = nickname
        self.aliasname = aliasname
        self.created_at = created_at
        self.updated_at = updated_at

    def __repr__(self):
        return "<User(qq='%s', nickname='%s', aliasname='%s', created_at='%s', created_at='%s')>" % (
            self.qq, self.nickname, self.aliasname, self.created_at, self.updated_at)


# 技能表
class Skill(Base):
    __tablename__ = 'skills'
    __table_args__ = {'mysql_engine': 'InnoDB', 'mysql_charset': 'utf8mb4'}

    id = Column(Integer, Sequence('skills_id_seq'), primary_key=True, nullable=False, index=True, unique=True)
    name = Column(String(64), nullable=False, index=True, unique=True, comment='技能名称')
    description = Column(String(64), nullable=True, comment='技能介绍')
    created_at = Column(DateTime, nullable=True)
    updated_at = Column(DateTime, nullable=True)

    avaiable_skills = relationship('UserSkill', back_populates='skill_used',
                                   cascade="all, delete", passive_deletes=True)

    def __init__(self, name, description=None, created_at=None, updated_at=None):
        self.name = name
        self.description = description
        self.created_at = created_at
        self.updated_at = updated_at

    def __repr__(self):
        return "<Skill(name='%s', description='%s', created_at='%s', created_at='%s')>" % (
            self.name, self.description, self.created_at, self.updated_at)


# 成员与技能表
class UserSkill(Base):
    __tablename__ = 'users_skills'
    __table_args__ = {'mysql_engine': 'InnoDB', 'mysql_charset': 'utf8mb4'}

    id = Column(Integer, Sequence('users_skills_id_seq'), primary_key=True, nullable=False, index=True, unique=True)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    skill_id = Column(Integer, ForeignKey('skills.id'), nullable=False)
    skill_level = Column(Integer, nullable=False, comment='技能等级')
    created_at = Column(DateTime, nullable=True)
    updated_at = Column(DateTime, nullable=True)

    user_skill = relationship('User', back_populates='has_skills')
    skill_used = relationship('Skill', back_populates='avaiable_skills')

    def __init__(self, user_id, skill_id, skill_level, created_at=None, updated_at=None):
        self.user_id = user_id
        self.skill_id = skill_id
        self.skill_level = skill_level
        self.created_at = created_at
        self.updated_at = updated_at

    def __repr__(self):
        return "<UserSkill(user_id='%s', skill_id='%s', skill_level='%s', created_at='%s', created_at='%s')>" % (
            self.user_id, self.skill_id, self.skill_level, self.created_at, self.updated_at)


# qq群表
class Group(Base):
    __tablename__ = 'groups'
    __table_args__ = {'mysql_engine': 'InnoDB', 'mysql_charset': 'utf8mb4'}

    id = Column(Integer, Sequence('groups_id_seq'), primary_key=True, nullable=False, index=True, unique=True)
    name = Column(String(64), nullable=False, comment='qq群名称')
    group_id = Column(Integer, nullable=False, index=True, unique=True, comment='qq群号')
    notice_permissions = Column(Integer, nullable=False, comment='通知权限')
    command_permissions = Column(Integer, nullable=False, comment='命令权限')
    permission_level = Column(Integer, nullable=False, comment='权限等级, 越大越高')
    created_at = Column(DateTime, nullable=True)
    updated_at = Column(DateTime, nullable=True)

    avaiable_groups = relationship('UserGroup', back_populates='groups_have_users',
                                   cascade="all, delete", passive_deletes=True)
    sub_what = relationship('GroupSub', back_populates='groups_sub',
                            cascade="all, delete", passive_deletes=True)
    group_auth = relationship('AuthGroup', back_populates='auth_for_group', uselist=False,
                              cascade="all, delete", passive_deletes=True)
    group_box = relationship('GroupEmailBox', back_populates='box_for_group',
                             cascade="all, delete", passive_deletes=True)

    def __init__(self, name, group_id, notice_permissions, command_permissions,
                 permission_level, created_at=None, updated_at=None):
        self.name = name
        self.group_id = group_id
        self.notice_permissions = notice_permissions
        self.command_permissions = command_permissions
        self.permission_level = permission_level
        self.created_at = created_at
        self.updated_at = updated_at

    def __repr__(self):
        return "<Group(name='%s', group_id='%s', notice_permissions='%s', " \
               "command_permissions='%s', permission_level='%s', created_at='%s', created_at='%s')>" % (
                   self.name, self.group_id, self.notice_permissions, self.command_permissions,
                   self.permission_level, self.created_at, self.updated_at)


# 成员与qq群表
class UserGroup(Base):
    __tablename__ = 'users_groups'
    __table_args__ = {'mysql_engine': 'InnoDB', 'mysql_charset': 'utf8mb4'}

    id = Column(Integer, Sequence('users_groups_id_seq'), primary_key=True, nullable=False, index=True, unique=True)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    group_id = Column(Integer, ForeignKey('groups.id'), nullable=False)
    user_group_nickname = Column(String(64), nullable=True, comment='用户群昵称')
    created_at = Column(DateTime, nullable=True)
    updated_at = Column(DateTime, nullable=True)

    user_groups = relationship('User', back_populates='in_which_groups')
    groups_have_users = relationship('Group', back_populates='avaiable_groups')

    def __init__(self, user_id, group_id, user_group_nickname=None, created_at=None, updated_at=None):
        self.user_id = user_id
        self.group_id = group_id
        self.user_group_nickname = user_group_nickname
        self.created_at = created_at
        self.updated_at = updated_at

    def __repr__(self):
        return "<UserGroup(user_id='%s', group_id='%s', " \
               "user_group_nickname='%s', created_at='%s', created_at='%s')>" % (
                   self.user_id, self.group_id, self.user_group_nickname, self.created_at, self.updated_at)


# 用户授权表
class AuthUser(Base):
    __tablename__ = 'auth_user'
    __table_args__ = {'mysql_engine': 'InnoDB', 'mysql_charset': 'utf8mb4'}

    id = Column(Integer, Sequence('auth_user_id_seq'), primary_key=True, nullable=False, index=True, unique=True)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    auth_node = Column(String(128), nullable=False, comment='授权节点, 由插件检查')
    allow_tag = Column(Integer, nullable=False, comment='授权标签')
    deny_tag = Column(Integer, nullable=False, comment='拒绝标签')
    auth_info = Column(String(128), nullable=True, comment='授权信息备注')
    created_at = Column(DateTime, nullable=True)
    updated_at = Column(DateTime, nullable=True)

    auth_for_user = relationship('User', back_populates='user_auth')

    def __init__(self, user_id, auth_node, allow_tag=0, deny_tag=0, auth_info=None, created_at=None, updated_at=None):
        self.user_id = user_id
        self.auth_node = auth_node
        self.allow_tag = allow_tag
        self.deny_tag = deny_tag
        self.auth_info = auth_info
        self.created_at = created_at
        self.updated_at = updated_at

    def __repr__(self):
        return "<AuthUser(user_id='%s', auth_node='%s', allow_tag='%s', deny_tag='%s', auth_info='%s', " \
               "created_at='%s', created_at='%s')>" % (
                   self.user_id, self.auth_node, self.allow_tag, self.deny_tag, self.auth_info,
                   self.created_at, self.updated_at)


# 群组授权表
class AuthGroup(Base):
    __tablename__ = 'auth_group'
    __table_args__ = {'mysql_engine': 'InnoDB', 'mysql_charset': 'utf8mb4'}

    id = Column(Integer, Sequence('auth_group_id_seq'), primary_key=True, nullable=False, index=True, unique=True)
    group_id = Column(Integer, ForeignKey('groups.id'), nullable=False)
    auth_node = Column(String(128), nullable=False, comment='授权节点, 由插件检查')
    allow_tag = Column(Integer, nullable=False, comment='授权标签')
    deny_tag = Column(Integer, nullable=False, comment='拒绝标签')
    auth_info = Column(String(128), nullable=True, comment='授权信息备注')
    created_at = Column(DateTime, nullable=True)
    updated_at = Column(DateTime, nullable=True)

    auth_for_group = relationship('Group', back_populates='group_auth')

    def __init__(self, group_id, auth_node, allow_tag=0, deny_tag=0, auth_info=None, created_at=None, updated_at=None):
        self.group_id = group_id
        self.auth_node = auth_node
        self.allow_tag = allow_tag
        self.deny_tag = deny_tag
        self.auth_info = auth_info
        self.created_at = created_at
        self.updated_at = updated_at

    def __repr__(self):
        return "<AuthGroup(group_id='%s', auth_node='%s', allow_tag='%s', deny_tag='%s', auth_info='%s', " \
               "created_at='%s', created_at='%s')>" % (
                   self.group_id, self.auth_node, self.allow_tag, self.deny_tag, self.auth_info,
                   self.created_at, self.updated_at)


# 邮箱表
class EmailBox(Base):
    __tablename__ = 'email_box'
    __table_args__ = {'mysql_engine': 'InnoDB', 'mysql_charset': 'utf8mb4'}

    id = Column(Integer, Sequence('email_box_id_seq'), primary_key=True, nullable=False, index=True, unique=True)
    address = Column(String(128), nullable=False, index=True, unique=True, comment='邮箱地址')
    server_host = Column(String(128), nullable=False, comment='IMAP服务器地址')
    protocol = Column(String(16), nullable=False, comment='协议')
    port = Column(Integer, nullable=False, comment='服务器端口')
    password = Column(String(256), nullable=False, comment='密码')
    created_at = Column(DateTime, nullable=True)
    updated_at = Column(DateTime, nullable=True)

    used_box = relationship('GroupEmailBox', back_populates='has_box',
                            cascade="all, delete", passive_deletes=True)

    def __init__(self, address: str, server_host: str, password: str,
                 protocol: str = 'imap', port: int = 993, created_at=None, updated_at=None):
        self.address = address
        self.server_host = server_host
        self.protocol = protocol
        self.port = port
        self.password = password
        self.created_at = created_at
        self.updated_at = updated_at

    def __repr__(self):
        return "<EmailBox(address='%s', server_host='%s', port='%s', port='%s', created_at='%s', updated_at='%s')>" % (
                   self.address, self.server_host, self.protocol, self.port, self.created_at, self.updated_at)


# 群组邮箱表
class GroupEmailBox(Base):
    __tablename__ = 'group_email_box'
    __table_args__ = {'mysql_engine': 'InnoDB', 'mysql_charset': 'utf8mb4'}

    id = Column(Integer, Sequence('group_email_box_id_seq'), primary_key=True, nullable=False, index=True, unique=True)
    email_box_id = Column(Integer, ForeignKey('email_box.id'), nullable=False)
    group_id = Column(Integer, ForeignKey('groups.id'), nullable=False)
    box_info = Column(String(64), nullable=True, comment='群邮箱信息，暂空备用')
    created_at = Column(DateTime, nullable=True)
    updated_at = Column(DateTime, nullable=True)

    box_for_group = relationship('Group', back_populates='group_box')

    has_box = relationship('EmailBox', back_populates='used_box')

    def __init__(self, email_box_id, group_id, box_info=None, created_at=None, updated_at=None):
        self.email_box_id = email_box_id
        self.group_id = group_id
        self.box_info = box_info
        self.created_at = created_at
        self.updated_at = updated_at

    def __repr__(self):
        return "<GroupEmailBox(email_box_id='%s', group_id='%s', box_info='%s', created_at='%s', created_at='%s')>" % (
                   self.email_box_id, self.group_id, self.box_info, self.created_at, self.updated_at)


# 邮件表
class Email(Base):
    __tablename__ = 'emails'
    __table_args__ = {'mysql_engine': 'InnoDB', 'mysql_charset': 'utf8mb4'}

    # 表结构
    id = Column(Integer, Sequence('emails_id_seq'), primary_key=True, nullable=False, index=True, unique=True)
    mail_hash = Column(String(128), nullable=False, index=True, unique=True, comment='邮件hash')
    date = Column(String(128), nullable=False, comment='时间')
    header = Column(String(128), nullable=False, comment='标题')
    sender = Column(String(128), nullable=False, comment='发件人')
    to = Column(String(1024), nullable=False, comment='收件人')
    body = Column(String(4096), nullable=True, comment='正文')
    html = Column(String(8192), nullable=True, comment='html正文')
    created_at = Column(DateTime, nullable=True)
    updated_at = Column(DateTime, nullable=True)

    def __init__(self, mail_hash, date, header, sender, to, body, html, created_at=None, updated_at=None):
        self.mail_hash = mail_hash
        self.date = date
        self.header = header
        self.sender = sender
        self.to = to
        self.body = body
        self.html = html
        self.created_at = created_at
        self.updated_at = updated_at

    def __repr__(self):
        return "<Email(mail_hash='%s',date='%s',header='%s',sender='%s'," \
               "to='%s', body='%s', html='%s', created_at='%s', created_at='%s')>" % (
                   self.mail_hash, self.date, self.header, self.sender,
                   self.to, self.body, self.html, self.created_at, self.updated_at)


# 记录表
class History(Base):
    __tablename__ = 'history'
    __table_args__ = {'mysql_engine': 'InnoDB', 'mysql_charset': 'utf8mb4'}

    # 表结构
    id = Column(Integer, Sequence('history_id_seq'), primary_key=True, nullable=False, index=True, unique=True)
    time = Column(BigInteger, nullable=False, comment='事件发生的时间戳')
    self_id = Column(BigInteger, nullable=False, comment='收到事件的机器人QQ号')
    post_type = Column(String(64), nullable=False, comment='事件类型')
    detail_type = Column(String(64), nullable=False, comment='消息/通知/请求/元事件类型')
    sub_type = Column(String(64), nullable=True, comment='子事件类型')
    group_id = Column(BigInteger, nullable=True, comment='群号')
    user_id = Column(BigInteger, nullable=True, comment='发送者QQ号')
    user_name = Column(String(64), nullable=True, comment='发送者名称')
    raw_data = Column(String(4096), nullable=True, comment='原始事件内容')
    msg_data = Column(String(4096), nullable=True, comment='经处理的事件内容')
    created_at = Column(DateTime, nullable=True)
    updated_at = Column(DateTime, nullable=True)

    def __init__(self, time, self_id, post_type, detail_type, sub_type=None,
                 group_id=None, user_id=None, user_name=None, raw_data=None, msg_data=None,
                 created_at=None, updated_at=None):
        self.time = time
        self.self_id = self_id
        self.post_type = post_type
        self.detail_type = detail_type
        self.sub_type = sub_type
        self.group_id = group_id
        self.user_id = user_id
        self.user_name = user_name
        self.raw_data = raw_data
        self.msg_data = msg_data
        self.created_at = created_at
        self.updated_at = updated_at

    def __repr__(self):
        return "<History(time='%s', self_id='%s', post_type='%s', detail_type='%s', sub_type='%s', group_id='%s', " \
               "user_id='%s', user_name='%s', raw_data='%s', msg_data='%s', created_at='%s', created_at='%s')>" % (
                   self.time, self.self_id, self.post_type, self.detail_type, self.sub_type,
                   self.group_id, self.user_id, self.user_name, self.raw_data, self.msg_data,
                   self.created_at, self.updated_at)


# 订阅表
class Subscription(Base):
    __tablename__ = 'subscription'
    __table_args__ = {'mysql_engine': 'InnoDB', 'mysql_charset': 'utf8mb4'}

    id = Column(Integer, Sequence('subscription_id_seq'), primary_key=True, nullable=False, index=True, unique=True)
    # 订阅类型, 0暂留, 1直播间, 2动态, 8Pixivsion
    sub_type = Column(Integer, nullable=False, comment='订阅类型，0暂留，1直播间，2动态')
    sub_id = Column(Integer, nullable=False, index=True, comment='订阅id，直播为直播间房间号，动态为用户uid')
    up_name = Column(String(64), nullable=False, comment='up名称')
    live_info = Column(String(64), nullable=True, comment='相关信息，暂空备用')
    created_at = Column(DateTime, nullable=True)
    updated_at = Column(DateTime, nullable=True)

    be_sub = relationship('GroupSub', back_populates='sub_by', cascade="all, delete", passive_deletes=True)

    def __init__(self, sub_type, sub_id, up_name, live_info=None, created_at=None, updated_at=None):
        self.sub_type = sub_type
        self.sub_id = sub_id
        self.up_name = up_name
        self.live_info = live_info
        self.created_at = created_at
        self.updated_at = updated_at

    def __repr__(self):
        return "<Subscription(sub_type='%s', sub_id='%s', up_name='%s', " \
               "live_info='%s', created_at='%s', created_at='%s')>" % (
                   self.sub_type, self.sub_id, self.up_name, self.live_info, self.created_at, self.updated_at)


# qq群订阅表
class GroupSub(Base):
    __tablename__ = 'groups_subs'
    __table_args__ = {'mysql_engine': 'InnoDB', 'mysql_charset': 'utf8mb4'}

    id = Column(Integer, Sequence('groups_subs_id_seq'), primary_key=True, nullable=False, index=True, unique=True)
    sub_id = Column(Integer, ForeignKey('subscription.id'), nullable=False)
    group_id = Column(Integer, ForeignKey('groups.id'), nullable=False)
    group_sub_info = Column(String(64), nullable=True, comment='群订阅信息，暂空备用')
    created_at = Column(DateTime, nullable=True)
    updated_at = Column(DateTime, nullable=True)

    groups_sub = relationship('Group', back_populates='sub_what')
    sub_by = relationship('Subscription', back_populates='be_sub')

    def __init__(self, sub_id, group_id, group_sub_info=None, created_at=None, updated_at=None):
        self.sub_id = sub_id
        self.group_id = group_id
        self.group_sub_info = group_sub_info
        self.created_at = created_at
        self.updated_at = updated_at

    def __repr__(self):
        return "<GroupSub(sub_id='%s', group_id='%s', " \
               "group_sub_info='%s', created_at='%s', created_at='%s')>" % (
                   self.sub_id, self.group_id, self.group_sub_info, self.created_at, self.updated_at)


# B站动态表
class Bilidynamic(Base):
    __tablename__ = 'bili_dynamics'
    __table_args__ = {'mysql_engine': 'InnoDB', 'mysql_charset': 'utf8mb4'}

    # 表结构
    id = Column(Integer, Sequence('bili_dynamics_id_seq'), primary_key=True, nullable=False, index=True, unique=True)
    uid = Column(Integer, nullable=False, index=True, comment='up的uid')
    dynamic_id = Column(BigInteger, nullable=False, index=True, unique=True, comment='动态的id')
    dynamic_type = Column(Integer, nullable=False, comment='动态的类型')
    content = Column(String(4096), nullable=False, comment='动态内容')
    created_at = Column(DateTime, nullable=True)
    updated_at = Column(DateTime, nullable=True)

    def __init__(self, uid, dynamic_id, dynamic_type, content, created_at=None, updated_at=None):
        self.uid = uid
        self.dynamic_id = dynamic_id
        self.dynamic_type = dynamic_type
        self.content = content
        self.created_at = created_at
        self.updated_at = updated_at

    def __repr__(self):
        return "<Bilidynamic(uid='%s',dynamic_id='%s',dynamic_type='%s'," \
               "content='%s', created_at='%s', created_at='%s')>" % (
                   self.uid, self.dynamic_id, self.dynamic_type,
                   self.content, self.created_at, self.updated_at)


# 假期表
class Vocation(Base):
    __tablename__ = 'vocations'
    __table_args__ = {'mysql_engine': 'InnoDB', 'mysql_charset': 'utf8mb4'}

    id = Column(Integer, Sequence('vocations_id_seq'), primary_key=True, nullable=False, index=True, unique=True)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    status = Column(Integer, nullable=False, comment='请假状态 0-空闲 1-请假 2-工作中')
    stop_at = Column(DateTime, nullable=True, comment='假期结束时间')
    reason = Column(String(64), nullable=True, comment='请假理由')
    created_at = Column(DateTime, nullable=True)
    updated_at = Column(DateTime, nullable=True)

    vocation_for_user = relationship('User', back_populates='vocation')

    def __init__(self, user_id, status, stop_at=None, reason=None, created_at=None, updated_at=None):
        self.user_id = user_id
        self.status = status
        self.stop_at = stop_at
        self.reason = reason
        self.created_at = created_at
        self.updated_at = updated_at

    def __repr__(self):
        return "<Vocation(user_id='%s',status='%s',stop_at='%s',reason='%s', created_at='%s', created_at='%s')>" % (
            self.user_id, self.status, self.stop_at, self.reason, self.created_at, self.updated_at)


# Pixiv tag表
class PixivTag(Base):
    __tablename__ = 'pixiv_tag'
    __table_args__ = {'mysql_engine': 'InnoDB', 'mysql_charset': 'utf8mb4'}

    id = Column(Integer, Sequence('pixiv_tag_id_seq'), primary_key=True, nullable=False, index=True, unique=True)
    tagname = Column(String(256), nullable=False, index=True, unique=True, comment='tag名称')
    created_at = Column(DateTime, nullable=True)
    updated_at = Column(DateTime, nullable=True)

    has_illusts = relationship('PixivT2I', back_populates='tag_has_illusts',
                               cascade="all, delete", passive_deletes=True)

    def __init__(self, tagname, created_at=None, updated_at=None):
        self.tagname = tagname
        self.created_at = created_at
        self.updated_at = updated_at

    def __repr__(self):
        return "<PixivTag(tagname='%s', created_at='%s', created_at='%s')>" % (
            self.tagname, self.created_at, self.updated_at)


# Pixiv作品表
class Pixiv(Base):
    __tablename__ = 'pixiv_illusts'
    __table_args__ = {'mysql_engine': 'InnoDB', 'mysql_charset': 'utf8mb4'}

    # 表结构
    id = Column(Integer, Sequence('upixiv_illusts_id_seq'), primary_key=True, nullable=False, index=True, unique=True)
    pid = Column(Integer, nullable=False, index=True, unique=True, comment='pid')
    uid = Column(Integer, nullable=False, comment='uid')
    title = Column(String(512), nullable=False, comment='title')
    uname = Column(String(256), nullable=False, comment='author')
    nsfw_tag = Column(Integer, nullable=False, comment='nsfw标签, 0=safe, 1=setu. 2=r18')
    tags = Column(String(2048), nullable=False, comment='tags')
    url = Column(String(2048), nullable=False, comment='url')
    created_at = Column(DateTime, nullable=True)
    updated_at = Column(DateTime, nullable=True)

    has_tags = relationship('PixivT2I', back_populates='illust_tags',
                            cascade="all, delete", passive_deletes=True)

    def __init__(self, pid, uid, title, uname, nsfw_tag, tags, url, created_at=None, updated_at=None):
        self.pid = pid
        self.uid = uid
        self.title = title
        self.uname = uname
        self.nsfw_tag = nsfw_tag
        self.tags = tags
        self.url = url
        self.created_at = created_at
        self.updated_at = updated_at

    def __repr__(self):
        return "<Pixiv(pid='%s',uid='%s',title='%s',uname='%s',nsfw_tag='%s'," \
               "tags='%s', url='%s', created_at='%s', created_at='%s')>" % (
                   self.pid, self.uid, self.title, self.uname, self.nsfw_tag,
                   self.tags, self.url, self.created_at, self.updated_at)


# Pixiv作品-tag表
class PixivT2I(Base):
    __tablename__ = 'pixiv_tag_to_illusts'
    __table_args__ = {'mysql_engine': 'InnoDB', 'mysql_charset': 'utf8mb4'}

    id = Column(Integer, Sequence('pixiv_tag_to_illusts_id_seq'),
                primary_key=True, nullable=False, index=True, unique=True)
    illust_id = Column(Integer, ForeignKey('pixiv_illusts.id'), nullable=False)
    tag_id = Column(Integer, ForeignKey('pixiv_tag.id'), nullable=False)
    created_at = Column(DateTime, nullable=True)
    updated_at = Column(DateTime, nullable=True)

    illust_tags = relationship('Pixiv', back_populates='has_tags')
    tag_has_illusts = relationship('PixivTag', back_populates='has_illusts')

    def __init__(self, illust_id, tag_id, created_at=None, updated_at=None):
        self.illust_id = illust_id
        self.tag_id = tag_id
        self.created_at = created_at
        self.updated_at = updated_at

    def __repr__(self):
        return "<PixivT2I(illust_id='%s', tag_id='%s', created_at='%s', created_at='%s')>" % (
            self.illust_id, self.tag_id, self.created_at, self.updated_at)


# Pixivision表
class Pixivision(Base):
    __tablename__ = 'pixivision_article'
    __table_args__ = {'mysql_engine': 'InnoDB', 'mysql_charset': 'utf8mb4'}

    # 表结构
    id = Column(Integer, Sequence('pixivision_article_id_seq'),
                primary_key=True, nullable=False, index=True, unique=True)
    aid = Column(Integer, nullable=False, index=True, unique=True, comment='aid')
    title = Column(String(256), nullable=False, comment='title')
    description = Column(String(1024), nullable=False, comment='description')
    tags = Column(String(1024), nullable=False, comment='tags')
    illust_id = Column(String(1024), nullable=False, comment='tags')
    url = Column(String(1024), nullable=False, comment='url')
    created_at = Column(DateTime, nullable=True)
    updated_at = Column(DateTime, nullable=True)

    def __init__(self, aid, title, description, tags, illust_id, url, created_at=None, updated_at=None):
        self.aid = aid
        self.title = title
        self.description = description
        self.tags = tags
        self.illust_id = illust_id
        self.url = url
        self.created_at = created_at
        self.updated_at = updated_at

    def __repr__(self):
        return "<Pixivision(aid='%s',title='%s',description='%s'," \
               "tags='%s', illust_id='%s', url='%s', created_at='%s', created_at='%s')>" % (
                   self.aid, self.title, self.description,
                   self.tags, self.illust_id, self.url, self.created_at, self.updated_at)


# 冷却事件表
class CoolDownEvent(Base):
    __tablename__ = 'cool_down_event'
    __table_args__ = {'mysql_engine': 'InnoDB', 'mysql_charset': 'utf8mb4'}

    # 表结构
    id = Column(Integer, Sequence('cool_down_event_id_seq'),
                primary_key=True, nullable=False, index=True, unique=True)
    event_type = Column(String(16), nullable=False, comment='冷却事件类型/global/plugin/group/user')
    stop_at = Column(DateTime, nullable=False, comment='冷却结束时间')
    plugin = Column(String(64), nullable=True, comment='plugin事件对应插件名')
    group_id = Column(Integer, nullable=True, comment='group事件对应group_id')
    user_id = Column(Integer, nullable=True, comment='user事件对应user_id')
    description = Column(String(128), nullable=True, comment='事件描述')
    created_at = Column(DateTime, nullable=True)
    updated_at = Column(DateTime, nullable=True)

    def __init__(self, event_type, stop_at, plugin=None, group_id=None, user_id=None, description=None,
                 created_at=None, updated_at=None):
        self.event_type = event_type
        self.stop_at = stop_at
        self.plugin = plugin
        self.group_id = group_id
        self.user_id = user_id
        self.description = description
        self.created_at = created_at
        self.updated_at = updated_at

    def __repr__(self):
        return "<CoolDownEvent(event_type='%s',stop_at='%s',plugin='%s'," \
               "group_id='%s', user_id='%s', description='%s', created_at='%s', created_at='%s')>" % (
                   self.event_type, self.stop_at, self.plugin,
                   self.group_id, self.user_id, self.description, self.created_at, self.updated_at)
