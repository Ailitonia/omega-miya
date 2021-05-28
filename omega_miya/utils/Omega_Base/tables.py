import nonebot
from sqlalchemy import Sequence, ForeignKey
from sqlalchemy import Column, Integer, BigInteger, String, DateTime
from sqlalchemy.orm import relationship
from sqlalchemy.ext.declarative import declarative_base


global_config = nonebot.get_driver().config
TABLE_PREFIX = global_config.db_table_prefix

# 创建数据表基类
Base = declarative_base()


# 系统参数表, 存放运行时状态
class OmegaStatus(Base):
    __tablename__ = f'{TABLE_PREFIX}status'
    __table_args__ = {'mysql_engine': 'InnoDB', 'mysql_charset': 'utf8mb4'}

    # 表结构
    id = Column(Integer, Sequence('omega_status_id_seq'), primary_key=True, nullable=False, index=True, unique=True)
    name = Column(String(32), nullable=False, index=True, unique=True, comment='参数名称')
    status = Column(Integer, nullable=False, comment='参数值')
    info = Column(String(128), nullable=True, comment='参数说明')
    created_at = Column(DateTime, nullable=True)
    updated_at = Column(DateTime, nullable=True)

    def __init__(self, name, status, info, created_at=None, updated_at=None):
        self.name = name
        self.status = status
        self.info = info
        self.created_at = created_at
        self.updated_at = updated_at

    def __repr__(self):
        return f"<OmegaStatus(name='{self.name}', status='{self.status}', info='{self.info}', " \
               f"created_at='{self.created_at}', updated_at='{self.updated_at}')>"


# Bot表 对应不同机器人协议端
class BotSelf(Base):
    __tablename__ = f'{TABLE_PREFIX}bots'
    __table_args__ = {'mysql_engine': 'InnoDB', 'mysql_charset': 'utf8mb4'}

    # 表结构
    id = Column(Integer, Sequence('bots_id_seq'), primary_key=True, nullable=False, index=True, unique=True)
    self_qq = Column(BigInteger, nullable=False, index=True, unique=True, comment='Bot的QQ号')
    status = Column(Integer, nullable=False, comment='在线状态')
    info = Column(String(1024), nullable=True, comment='信息')
    created_at = Column(DateTime, nullable=True)
    updated_at = Column(DateTime, nullable=True)

    # 设置级联和关系加载
    bots_bot_friends = relationship('Friends', back_populates='bot_friends_back_bots',
                                    cascade='all, delete-orphan', passive_deletes=True)
    bots_bot_groups = relationship('BotGroup', back_populates='bot_groups_back_bots',
                                   cascade='all, delete-orphan', passive_deletes=True)

    def __init__(self, self_qq, status, info=None, created_at=None, updated_at=None):
        self.self_qq = self_qq
        self.status = status
        self.info = info
        self.created_at = created_at
        self.updated_at = updated_at

    def __repr__(self):
        return f"<BotSelf(self_qq='{self.self_qq}', info='{self.info}', status='{self.status}' " \
               f"created_at='{self.created_at}', updated_at='{self.updated_at}')>"


# 成员表
class User(Base):
    __tablename__ = f'{TABLE_PREFIX}users'
    __table_args__ = {'mysql_engine': 'InnoDB', 'mysql_charset': 'utf8mb4'}

    # 表结构
    id = Column(Integer, Sequence('users_id_seq'), primary_key=True, nullable=False, index=True, unique=True)
    qq = Column(BigInteger, nullable=False, index=True, unique=True, comment='QQ号')
    nickname = Column(String(64), nullable=False, comment='昵称')
    aliasname = Column(String(64), nullable=True, comment='自定义名称')
    created_at = Column(DateTime, nullable=True)
    updated_at = Column(DateTime, nullable=True)

    # 设置级联和关系加载
    users_bot_friends = relationship('Friends', back_populates='bot_friends_back_users',
                                     cascade='all, delete-orphan', passive_deletes=True)
    users_users_groups = relationship('UserGroup', back_populates='users_groups_back_users',
                                      cascade='all, delete-orphan', passive_deletes=True)
    users_users_skills = relationship('UserSkill', back_populates='users_skills_back_users',
                                      cascade='all, delete-orphan', passive_deletes=True)
    users_vocations = relationship('Vocation', back_populates='vocations_back_users',
                                   cascade='all, delete-orphan', passive_deletes=True)

    def __init__(self, qq, nickname, aliasname=None, created_at=None, updated_at=None):
        self.qq = qq
        self.nickname = nickname
        self.aliasname = aliasname
        self.created_at = created_at
        self.updated_at = updated_at

    def __repr__(self):
        return f"<User(qq='{self.qq}', nickname='{self.nickname}', aliasname='{self.aliasname}', " \
               f"created_at='{self.created_at}', updated_at='{self.updated_at}')>"


# 好友表
class Friends(Base):
    __tablename__ = f'{TABLE_PREFIX}bot_friends'
    __table_args__ = {'mysql_engine': 'InnoDB', 'mysql_charset': 'utf8mb4'}

    # 表结构
    id = Column(Integer, Sequence('bot_friends_id_seq'), primary_key=True, nullable=False, index=True, unique=True)
    user_id = Column(Integer, ForeignKey(f'{TABLE_PREFIX}users.id', ondelete='CASCADE'), nullable=False)
    bot_self_id = Column(Integer, ForeignKey(f'{TABLE_PREFIX}bots.id', ondelete='CASCADE'), nullable=False)
    nickname = Column(String(64), nullable=False, comment='昵称')
    remark = Column(String(64), nullable=True, comment='备注')
    private_permissions = Column(Integer, nullable=False, comment='是否启用私聊权限')
    created_at = Column(DateTime, nullable=True)
    updated_at = Column(DateTime, nullable=True)

    # 设置级联和关系加载
    bot_friends_back_bots = relationship(BotSelf, back_populates='bots_bot_friends', lazy='joined', innerjoin=True)
    bot_friends_back_users = relationship(User, back_populates='users_bot_friends', lazy='joined', innerjoin=True)
    bot_friends_auth_user = relationship('AuthUser', back_populates='auth_user_back_bot_friends',
                                         cascade='all, delete-orphan', passive_deletes=True)
    bot_friends_users_subs = relationship('UserSub', back_populates='users_subs_back_bot_friends',
                                          cascade='all, delete-orphan', passive_deletes=True)

    def __init__(self, user_id, bot_self_id, nickname,
                 remark=None, private_permissions=0, created_at=None, updated_at=None):
        self.user_id = user_id
        self.bot_self_id = bot_self_id
        self.nickname = nickname
        self.remark = remark
        self.private_permissions = private_permissions
        self.created_at = created_at
        self.updated_at = updated_at

    def __repr__(self):
        return f"<Friends(user_id='{self.user_id}', bot_self_id='{self.bot_self_id}', " \
               f"nickname='{self.nickname}', remark='{self.remark}', " \
               f"private_permissions='{self.private_permissions}', " \
               f"created_at='{self.created_at}', updated_at='{self.updated_at}')>"


# 技能表
class Skill(Base):
    __tablename__ = f'{TABLE_PREFIX}skills'
    __table_args__ = {'mysql_engine': 'InnoDB', 'mysql_charset': 'utf8mb4'}

    id = Column(Integer, Sequence('skills_id_seq'), primary_key=True, nullable=False, index=True, unique=True)
    name = Column(String(64), nullable=False, index=True, unique=True, comment='技能名称')
    description = Column(String(64), nullable=True, comment='技能介绍')
    created_at = Column(DateTime, nullable=True)
    updated_at = Column(DateTime, nullable=True)

    # 设置级联和关系加载
    skills_users_skills = relationship('UserSkill', back_populates='users_skills_back_skills',
                                       cascade='all, delete-orphan', passive_deletes=True)

    def __init__(self, name, description=None, created_at=None, updated_at=None):
        self.name = name
        self.description = description
        self.created_at = created_at
        self.updated_at = updated_at

    def __repr__(self):
        return f"<Skill(name='{self.name}', description='{self.description}', " \
               f"created_at='{self.created_at}', updated_at='{self.updated_at}')>"


# 成员与技能表
class UserSkill(Base):
    __tablename__ = f'{TABLE_PREFIX}users_skills'
    __table_args__ = {'mysql_engine': 'InnoDB', 'mysql_charset': 'utf8mb4'}

    id = Column(Integer, Sequence('users_skills_id_seq'), primary_key=True, nullable=False, index=True, unique=True)
    user_id = Column(Integer, ForeignKey(f'{TABLE_PREFIX}users.id', ondelete='CASCADE'), nullable=False)
    skill_id = Column(Integer, ForeignKey(f'{TABLE_PREFIX}skills.id', ondelete='CASCADE'), nullable=False)
    skill_level = Column(Integer, nullable=False, comment='技能等级')
    created_at = Column(DateTime, nullable=True)
    updated_at = Column(DateTime, nullable=True)

    # 设置级联和关系加载
    users_skills_back_users = relationship(User, back_populates='users_users_skills', lazy='joined', innerjoin=True)
    users_skills_back_skills = relationship(Skill, back_populates='skills_users_skills', lazy='joined', innerjoin=True)

    def __init__(self, user_id, skill_id, skill_level, created_at=None, updated_at=None):
        self.user_id = user_id
        self.skill_id = skill_id
        self.skill_level = skill_level
        self.created_at = created_at
        self.updated_at = updated_at

    def __repr__(self):
        return f"<UserSkill(user_id='{self.user_id}', skill_id='{self.skill_id}', skill_level='{self.skill_level}', " \
               f"created_at='{self.created_at}', updated_at='{self.updated_at}')>"


# qq群表
class Group(Base):
    __tablename__ = f'{TABLE_PREFIX}groups'
    __table_args__ = {'mysql_engine': 'InnoDB', 'mysql_charset': 'utf8mb4'}

    id = Column(Integer, Sequence('groups_id_seq'), primary_key=True, nullable=False, index=True, unique=True)
    name = Column(String(64), nullable=False, comment='qq群名称')
    group_id = Column(BigInteger, nullable=False, index=True, unique=True, comment='qq群号')
    created_at = Column(DateTime, nullable=True)
    updated_at = Column(DateTime, nullable=True)

    # 设置级联和关系加载
    groups_bot_groups = relationship('BotGroup', back_populates='bot_groups_back_groups',
                                     cascade='all, delete-orphan', passive_deletes=True)

    def __init__(self, name, group_id, created_at=None, updated_at=None):
        self.name = name
        self.group_id = group_id
        self.created_at = created_at
        self.updated_at = updated_at

    def __repr__(self):
        return f"<Group(name='{self.name}', group_id='{self.group_id}', " \
               f"created_at='{self.created_at}', updated_at='{self.updated_at}')>"


# Bot对应qq群表
class BotGroup(Base):
    __tablename__ = f'{TABLE_PREFIX}bot_groups'
    __table_args__ = {'mysql_engine': 'InnoDB', 'mysql_charset': 'utf8mb4'}

    id = Column(Integer, Sequence('bot_groups_id_seq'), primary_key=True, nullable=False, index=True, unique=True)
    group_id = Column(Integer, ForeignKey(f'{TABLE_PREFIX}groups.id', ondelete='CASCADE'), nullable=False)
    bot_self_id = Column(Integer, ForeignKey(f'{TABLE_PREFIX}bots.id', ondelete='CASCADE'), nullable=False)
    group_memo = Column(String(64), nullable=True, comment='群备注')
    notice_permissions = Column(Integer, nullable=False, comment='通知权限')
    command_permissions = Column(Integer, nullable=False, comment='命令权限')
    permission_level = Column(Integer, nullable=False, comment='权限等级, 越大越高')
    created_at = Column(DateTime, nullable=True)
    updated_at = Column(DateTime, nullable=True)

    # 设置级联和关系加载
    bot_groups_back_bots = relationship(BotSelf, back_populates='bots_bot_groups', lazy='joined', innerjoin=True)
    bot_groups_back_groups = relationship(Group, back_populates='groups_bot_groups', lazy='joined', innerjoin=True)
    bot_groups_users_groups = relationship('UserGroup', back_populates='users_groups_back_bot_groups',
                                           cascade='all, delete-orphan', passive_deletes=True)
    bot_groups_groups_subs = relationship('GroupSub', back_populates='groups_subs_back_bot_groups',
                                          cascade='all, delete-orphan', passive_deletes=True)
    bot_groups_auth_group = relationship('AuthGroup', back_populates='auth_group_back_bot_groups',
                                         cascade='all, delete-orphan', passive_deletes=True)
    bot_groups_group_email_box = relationship('GroupEmailBox', back_populates='group_email_box_back_bot_groups',
                                              cascade='all, delete-orphan', passive_deletes=True)

    def __init__(self, group_id, bot_self_id, notice_permissions, command_permissions,
                 permission_level, group_memo=None, created_at=None, updated_at=None):
        self.group_id = group_id
        self.bot_self_id = bot_self_id
        self.group_memo = group_memo
        self.notice_permissions = notice_permissions
        self.command_permissions = command_permissions
        self.permission_level = permission_level
        self.created_at = created_at
        self.updated_at = updated_at

    def __repr__(self):
        return f"<Group(group_id='{self.group_id}', bot_self_id='{self.bot_self_id}', " \
               f"group_memo='{self.group_memo}', notice_permissions='{self.notice_permissions}', " \
               f"command_permissions='{self.command_permissions}', permission_level='{self.permission_level}', " \
               f"created_at='{self.created_at}', updated_at='{self.updated_at}')>"


# 成员与qq群表
class UserGroup(Base):
    __tablename__ = f'{TABLE_PREFIX}users_groups'
    __table_args__ = {'mysql_engine': 'InnoDB', 'mysql_charset': 'utf8mb4'}

    id = Column(Integer, Sequence('users_groups_id_seq'), primary_key=True, nullable=False, index=True, unique=True)
    user_id = Column(Integer, ForeignKey(f'{TABLE_PREFIX}users.id', ondelete='CASCADE'), nullable=False)
    group_id = Column(Integer, ForeignKey(f'{TABLE_PREFIX}bot_groups.id', ondelete='CASCADE'), nullable=False)
    user_group_nickname = Column(String(64), nullable=True, comment='用户群昵称')
    created_at = Column(DateTime, nullable=True)
    updated_at = Column(DateTime, nullable=True)

    # 设置级联和关系加载
    users_groups_back_users = relationship(User, back_populates='users_users_groups', lazy='joined', innerjoin=True)
    users_groups_back_bot_groups = relationship(BotGroup, back_populates='bot_groups_users_groups',
                                                lazy='joined', innerjoin=True)

    def __init__(self, user_id, group_id, user_group_nickname=None, created_at=None, updated_at=None):
        self.user_id = user_id
        self.group_id = group_id
        self.user_group_nickname = user_group_nickname
        self.created_at = created_at
        self.updated_at = updated_at

    def __repr__(self):
        return f"<UserGroup(user_id='{self.user_id}', group_id='{self.group_id}', " \
               f"user_group_nickname='{self.user_group_nickname}', " \
               f"created_at='{self.created_at}', updated_at='{self.updated_at}')>"


# 用户授权表
class AuthUser(Base):
    __tablename__ = f'{TABLE_PREFIX}auth_user'
    __table_args__ = {'mysql_engine': 'InnoDB', 'mysql_charset': 'utf8mb4'}

    id = Column(Integer, Sequence('auth_user_id_seq'), primary_key=True, nullable=False, index=True, unique=True)
    user_id = Column(Integer, ForeignKey(f'{TABLE_PREFIX}bot_friends.id', ondelete='CASCADE'), nullable=False)
    auth_node = Column(String(128), nullable=False, index=True, comment='授权节点, 由插件检查')
    allow_tag = Column(Integer, nullable=False, comment='授权标签')
    deny_tag = Column(Integer, nullable=False, comment='拒绝标签')
    auth_info = Column(String(128), nullable=True, comment='授权信息备注')
    created_at = Column(DateTime, nullable=True)
    updated_at = Column(DateTime, nullable=True)

    # 设置级联和关系加载
    auth_user_back_bot_friends = relationship(Friends, back_populates='bot_friends_auth_user',
                                              lazy='joined', innerjoin=True)

    def __init__(self, user_id, auth_node, allow_tag=0, deny_tag=0, auth_info=None, created_at=None, updated_at=None):
        self.user_id = user_id
        self.auth_node = auth_node
        self.allow_tag = allow_tag
        self.deny_tag = deny_tag
        self.auth_info = auth_info
        self.created_at = created_at
        self.updated_at = updated_at

    def __repr__(self):
        return f"<AuthUser(user_id='{self.user_id}', auth_node='{self.auth_node}', " \
               f"allow_tag='{self.allow_tag}', deny_tag='{self.deny_tag}', auth_info='{self.auth_info}', " \
               f"created_at='{self.created_at}', updated_at='{self.updated_at}')>"


# 群组授权表
class AuthGroup(Base):
    __tablename__ = f'{TABLE_PREFIX}auth_group'
    __table_args__ = {'mysql_engine': 'InnoDB', 'mysql_charset': 'utf8mb4'}

    id = Column(Integer, Sequence('auth_group_id_seq'), primary_key=True, nullable=False, index=True, unique=True)
    group_id = Column(Integer, ForeignKey(f'{TABLE_PREFIX}bot_groups.id', ondelete='CASCADE'), nullable=False)
    auth_node = Column(String(128), nullable=False, index=True, comment='授权节点, 由插件检查')
    allow_tag = Column(Integer, nullable=False, comment='授权标签')
    deny_tag = Column(Integer, nullable=False, comment='拒绝标签')
    auth_info = Column(String(128), nullable=True, comment='授权信息备注')
    created_at = Column(DateTime, nullable=True)
    updated_at = Column(DateTime, nullable=True)

    # 设置级联和关系加载
    auth_group_back_bot_groups = relationship(BotGroup, back_populates='bot_groups_auth_group',
                                              lazy='joined', innerjoin=True)

    def __init__(self, group_id, auth_node, allow_tag=0, deny_tag=0, auth_info=None, created_at=None, updated_at=None):
        self.group_id = group_id
        self.auth_node = auth_node
        self.allow_tag = allow_tag
        self.deny_tag = deny_tag
        self.auth_info = auth_info
        self.created_at = created_at
        self.updated_at = updated_at

    def __repr__(self):
        return f"<AuthGroup(group_id='{self.group_id}', auth_node='{self.auth_node}', " \
               f"allow_tag='{self.allow_tag}', deny_tag='{self.deny_tag}', auth_info='{self.auth_info}', " \
               f"created_at='{self.created_at}', updated_at='{self.updated_at}')>"


# 邮箱表
class EmailBox(Base):
    __tablename__ = f'{TABLE_PREFIX}email_box'
    __table_args__ = {'mysql_engine': 'InnoDB', 'mysql_charset': 'utf8mb4'}

    id = Column(Integer, Sequence('email_box_id_seq'), primary_key=True, nullable=False, index=True, unique=True)
    address = Column(String(128), nullable=False, index=True, unique=True, comment='邮箱地址')
    server_host = Column(String(128), nullable=False, comment='IMAP服务器地址')
    protocol = Column(String(16), nullable=False, comment='协议')
    port = Column(Integer, nullable=False, comment='服务器端口')
    password = Column(String(256), nullable=False, comment='密码')
    created_at = Column(DateTime, nullable=True)
    updated_at = Column(DateTime, nullable=True)

    # 设置级联和关系加载
    email_box_group_email_box = relationship('GroupEmailBox', back_populates='group_email_box_back_email_box',
                                             cascade='all, delete-orphan', passive_deletes=True)

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
        return f"<EmailBox(address='{self.address}', server_host='{self.server_host}', " \
               f"protocol='{self.protocol}', port='{self.port}', " \
               f"created_at='{self.created_at}', updated_at='{self.updated_at}')>"


# 群组邮箱表
class GroupEmailBox(Base):
    __tablename__ = f'{TABLE_PREFIX}group_email_box'
    __table_args__ = {'mysql_engine': 'InnoDB', 'mysql_charset': 'utf8mb4'}

    id = Column(Integer, Sequence('group_email_box_id_seq'), primary_key=True, nullable=False, index=True, unique=True)
    email_box_id = Column(Integer, ForeignKey(f'{TABLE_PREFIX}email_box.id', ondelete='CASCADE'), nullable=False)
    group_id = Column(Integer, ForeignKey(f'{TABLE_PREFIX}bot_groups.id', ondelete='CASCADE'), nullable=False)
    box_info = Column(String(64), nullable=True, comment='群邮箱信息，暂空备用')
    created_at = Column(DateTime, nullable=True)
    updated_at = Column(DateTime, nullable=True)

    # 设置级联和关系加载
    group_email_box_back_bot_groups = relationship(BotGroup, back_populates='bot_groups_group_email_box',
                                                   lazy='joined', innerjoin=True)
    group_email_box_back_email_box = relationship(EmailBox, back_populates='email_box_group_email_box',
                                                  lazy='joined', innerjoin=True)

    def __init__(self, email_box_id, group_id, box_info=None, created_at=None, updated_at=None):
        self.email_box_id = email_box_id
        self.group_id = group_id
        self.box_info = box_info
        self.created_at = created_at
        self.updated_at = updated_at

    def __repr__(self):
        return f"<GroupEmailBox(email_box_id='{self.email_box_id}', group_id='{self.group_id}', " \
               f"box_info='{self.box_info}', created_at='{self.created_at}', updated_at='{self.updated_at}')>"


# 邮件表
class Email(Base):
    __tablename__ = f'{TABLE_PREFIX}emails'
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
        return f"<Email(mail_hash='{self.mail_hash}', date='{self.date}', " \
               f"header='{self.header}', sender='{self.sender}', to='{self.to}', " \
               f"body='{self.body}', html='{self.html}', " \
               f"created_at='{self.created_at}', updated_at='{self.updated_at}')>"


# 记录表
class History(Base):
    __tablename__ = f'{TABLE_PREFIX}history'
    __table_args__ = {'mysql_engine': 'InnoDB', 'mysql_charset': 'utf8mb4'}

    # 表结构
    id = Column(Integer, Sequence('history_id_seq'), primary_key=True, nullable=False, index=True, unique=True)
    time = Column(BigInteger, nullable=False, comment='事件发生的时间戳')
    self_id = Column(BigInteger, nullable=False, index=True, comment='收到事件的机器人QQ号')
    post_type = Column(String(64), nullable=False, index=True, comment='事件类型')
    detail_type = Column(String(64), nullable=False, index=True, comment='消息/通知/请求/元事件类型')
    sub_type = Column(String(64), nullable=False, index=True, comment='子事件类型')
    event_id = Column(BigInteger, nullable=False, index=True, comment='事件id, 消息事件为message_id')
    group_id = Column(BigInteger, nullable=False, index=True, comment='群号')
    user_id = Column(BigInteger, nullable=False, index=True, comment='发送者QQ号')
    user_name = Column(String(64), nullable=True, comment='发送者名称')
    raw_data = Column(String(4096), nullable=True, comment='原始事件内容')
    msg_data = Column(String(4096), nullable=True, comment='经处理的事件内容')
    created_at = Column(DateTime, nullable=True)
    updated_at = Column(DateTime, nullable=True)

    def __init__(self, time, self_id, post_type, detail_type, sub_type='Undefined', event_id=0,
                 group_id=-1, user_id=-1, user_name=None, raw_data=None, msg_data=None,
                 created_at=None, updated_at=None):
        self.time = time
        self.self_id = self_id
        self.post_type = post_type
        self.detail_type = detail_type
        self.sub_type = sub_type
        self.event_id = event_id
        self.group_id = group_id
        self.user_id = user_id
        self.user_name = user_name
        self.raw_data = raw_data
        self.msg_data = msg_data
        self.created_at = created_at
        self.updated_at = updated_at

    def __repr__(self):
        return f"<History(time='{self.time}', self_id='{self.self_id}', post_type='{self.post_type}', " \
               f"detail_type='{self.detail_type}', sub_type='{self.sub_type}', event_id='{self.event_id}', " \
               f"group_id='{self.group_id}', user_id='{self.user_id}', user_name='{self.user_name}', " \
               f"raw_data='{self.raw_data}', msg_data='{self.msg_data}', " \
               f"created_at='{self.created_at}', updated_at='{self.updated_at}')>"


# 订阅表
class Subscription(Base):
    __tablename__ = f'{TABLE_PREFIX}subscription'
    __table_args__ = {'mysql_engine': 'InnoDB', 'mysql_charset': 'utf8mb4'}

    id = Column(Integer, Sequence('subscription_id_seq'), primary_key=True, nullable=False, index=True, unique=True)
    # 订阅类型, 0暂留, 1直播间, 2动态, 8Pixivsion
    sub_type = Column(Integer, nullable=False, comment='订阅类型，0暂留，1直播间，2动态')
    sub_id = Column(Integer, nullable=False, index=True, comment='订阅id，直播为直播间房间号，动态为用户uid')
    up_name = Column(String(64), nullable=False, comment='up名称')
    live_info = Column(String(64), nullable=True, comment='相关信息，暂空备用')
    created_at = Column(DateTime, nullable=True)
    updated_at = Column(DateTime, nullable=True)

    # 设置级联和关系加载
    subscription_groups_subs = relationship('GroupSub', back_populates='groups_subs_back_subscription',
                                            cascade='all, delete-orphan', passive_deletes=True)
    subscription_users_subs = relationship('UserSub', back_populates='users_subs_back_subscription',
                                           cascade='all, delete-orphan', passive_deletes=True)

    def __init__(self, sub_type, sub_id, up_name, live_info=None, created_at=None, updated_at=None):
        self.sub_type = sub_type
        self.sub_id = sub_id
        self.up_name = up_name
        self.live_info = live_info
        self.created_at = created_at
        self.updated_at = updated_at

    def __repr__(self):
        return f"<Subscription(sub_type='{self.sub_type}', sub_id='{self.sub_id}', up_name='{self.up_name}', " \
               f"live_info='{self.live_info}', created_at='{self.created_at}', updated_at='{self.updated_at}')>"


# qq群订阅表
class GroupSub(Base):
    __tablename__ = f'{TABLE_PREFIX}groups_subs'
    __table_args__ = {'mysql_engine': 'InnoDB', 'mysql_charset': 'utf8mb4'}

    id = Column(Integer, Sequence('groups_subs_id_seq'), primary_key=True, nullable=False, index=True, unique=True)
    sub_id = Column(Integer, ForeignKey(f'{TABLE_PREFIX}subscription.id', ondelete='CASCADE'), nullable=False)
    group_id = Column(Integer, ForeignKey(f'{TABLE_PREFIX}bot_groups.id', ondelete='CASCADE'), nullable=False)
    group_sub_info = Column(String(64), nullable=True, comment='群订阅信息，暂空备用')
    created_at = Column(DateTime, nullable=True)
    updated_at = Column(DateTime, nullable=True)

    # 设置级联和关系加载
    groups_subs_back_bot_groups = relationship(BotGroup, back_populates='bot_groups_groups_subs',
                                               lazy='joined', innerjoin=True)
    groups_subs_back_subscription = relationship(Subscription, back_populates='subscription_groups_subs',
                                                 lazy='joined', innerjoin=True)

    def __init__(self, sub_id, group_id, group_sub_info=None, created_at=None, updated_at=None):
        self.sub_id = sub_id
        self.group_id = group_id
        self.group_sub_info = group_sub_info
        self.created_at = created_at
        self.updated_at = updated_at

    def __repr__(self):
        return f"<GroupSub(sub_id='{self.sub_id}', group_id='{self.group_id}', " \
               f"group_sub_info='{self.group_sub_info}', " \
               f"created_at='{self.created_at}', updated_at='{self.updated_at}')>"


# 好友用户订阅表
class UserSub(Base):
    __tablename__ = f'{TABLE_PREFIX}users_subs'
    __table_args__ = {'mysql_engine': 'InnoDB', 'mysql_charset': 'utf8mb4'}

    id = Column(Integer, Sequence('users_subs_id_seq'), primary_key=True, nullable=False, index=True, unique=True)
    sub_id = Column(Integer, ForeignKey(f'{TABLE_PREFIX}subscription.id', ondelete='CASCADE'), nullable=False)
    user_id = Column(Integer, ForeignKey(f'{TABLE_PREFIX}bot_friends.id', ondelete='CASCADE'), nullable=False)
    user_sub_info = Column(String(64), nullable=True, comment='用户订阅信息，暂空备用')
    created_at = Column(DateTime, nullable=True)
    updated_at = Column(DateTime, nullable=True)

    # 设置级联和关系加载
    users_subs_back_bot_friends = relationship(Friends, back_populates='bot_friends_users_subs',
                                               lazy='joined', innerjoin=True)
    users_subs_back_subscription = relationship(Subscription, back_populates='subscription_users_subs',
                                                lazy='joined', innerjoin=True)

    def __init__(self, sub_id, user_id, user_sub_info=None, created_at=None, updated_at=None):
        self.sub_id = sub_id
        self.user_id = user_id
        self.user_sub_info = user_sub_info
        self.created_at = created_at
        self.updated_at = updated_at

    def __repr__(self):
        return f"<UserSub(sub_id='{self.sub_id}', user_id='{self.user_id}', " \
               f"user_sub_info='{self.user_sub_info}', " \
               f"created_at='{self.created_at}', updated_at='{self.updated_at}')>"


# B站动态表
class Bilidynamic(Base):
    __tablename__ = f'{TABLE_PREFIX}bili_dynamics'
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
        return f"<Bilidynamic(uid='{self.uid}', dynamic_id='{self.dynamic_id}', " \
               f"dynamic_type='{self.dynamic_type}', content='{self.content}', " \
               f"created_at='{self.created_at}', updated_at='{self.updated_at}')>"


# 假期表
class Vocation(Base):
    __tablename__ = f'{TABLE_PREFIX}vocations'
    __table_args__ = {'mysql_engine': 'InnoDB', 'mysql_charset': 'utf8mb4'}

    id = Column(Integer, Sequence('vocations_id_seq'), primary_key=True, nullable=False, index=True, unique=True)
    user_id = Column(Integer, ForeignKey(f'{TABLE_PREFIX}users.id', ondelete='CASCADE'), nullable=False)
    status = Column(Integer, nullable=False, comment='请假状态 0-空闲 1-请假 2-工作中')
    stop_at = Column(DateTime, nullable=True, comment='假期结束时间')
    reason = Column(String(64), nullable=True, comment='请假理由')
    created_at = Column(DateTime, nullable=True)
    updated_at = Column(DateTime, nullable=True)

    # 设置级联和关系加载
    vocations_back_users = relationship(User, back_populates='users_vocations', lazy='joined', innerjoin=True)

    def __init__(self, user_id, status, stop_at=None, reason=None, created_at=None, updated_at=None):
        self.user_id = user_id
        self.status = status
        self.stop_at = stop_at
        self.reason = reason
        self.created_at = created_at
        self.updated_at = updated_at

    def __repr__(self):
        return f"<Vocation(user_id='{self.user_id}', status='{self.status}', stop_at='{self.stop_at}', " \
               f"reason='{self.reason}', created_at='{self.created_at}', updated_at='{self.updated_at}')>"


# Pixiv tag表
class PixivTag(Base):
    __tablename__ = f'{TABLE_PREFIX}pixiv_tag'
    __table_args__ = {'mysql_engine': 'InnoDB', 'mysql_charset': 'utf8mb4'}

    id = Column(Integer, Sequence('pixiv_tag_id_seq'), primary_key=True, nullable=False, index=True, unique=True)
    tagname = Column(String(128), nullable=False, index=True, unique=True, comment='tag名称')
    created_at = Column(DateTime, nullable=True)
    updated_at = Column(DateTime, nullable=True)

    # 设置级联和关系加载
    pixiv_tag_pixiv_tag_to_illusts = relationship('PixivT2I', back_populates='pixiv_tag_to_illusts_back_pixiv_tag',
                                                  cascade='all, delete-orphan', passive_deletes=True)

    def __init__(self, tagname, created_at=None, updated_at=None):
        self.tagname = tagname
        self.created_at = created_at
        self.updated_at = updated_at

    def __repr__(self):
        return f"<PixivTag(tagname='{self.tagname}', " \
               f"created_at='{self.created_at}', updated_at='{self.updated_at}')>"


# Pixiv作品表
class Pixiv(Base):
    __tablename__ = f'{TABLE_PREFIX}pixiv_illusts'
    __table_args__ = {'mysql_engine': 'InnoDB', 'mysql_charset': 'utf8mb4'}

    # 表结构
    id = Column(Integer, Sequence('upixiv_illusts_id_seq'), primary_key=True, nullable=False, index=True, unique=True)
    pid = Column(Integer, nullable=False, index=True, unique=True, comment='pid')
    uid = Column(Integer, nullable=False, index=True, comment='uid')
    title = Column(String(128), nullable=False, index=True, comment='title')
    uname = Column(String(128), nullable=False, index=True, comment='author')
    nsfw_tag = Column(Integer, nullable=False, comment='nsfw标签, 0=safe, 1=setu. 2=r18')
    tags = Column(String(1024), nullable=False, comment='tags')
    url = Column(String(1024), nullable=False, comment='url')
    created_at = Column(DateTime, nullable=True)
    updated_at = Column(DateTime, nullable=True)

    # 设置级联和关系加载
    pixiv_illusts_pixiv_tag_to_illusts = relationship('PixivT2I',
                                                      back_populates='pixiv_tag_to_illusts_back_pixiv_illusts',
                                                      cascade='all, delete-orphan', passive_deletes=True)

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
        return f"<Pixiv(pid='{self.pid}', uid='{self.uid}', title='{self.title}', uname='{self.uname}', " \
               f"nsfw_tag='{self.nsfw_tag}', tags='{self.tags}', url='{self.url}', " \
               f"created_at='{self.created_at}', updated_at='{self.updated_at}')>"


# Pixiv作品-tag表
class PixivT2I(Base):
    __tablename__ = f'{TABLE_PREFIX}pixiv_tag_to_illusts'
    __table_args__ = {'mysql_engine': 'InnoDB', 'mysql_charset': 'utf8mb4'}

    id = Column(Integer, Sequence('pixiv_tag_to_illusts_id_seq'),
                primary_key=True, nullable=False, index=True, unique=True)
    illust_id = Column(Integer, ForeignKey(f'{TABLE_PREFIX}pixiv_illusts.id', ondelete='CASCADE'), nullable=False)
    tag_id = Column(Integer, ForeignKey(f'{TABLE_PREFIX}pixiv_tag.id', ondelete='CASCADE'), nullable=False)
    created_at = Column(DateTime, nullable=True)
    updated_at = Column(DateTime, nullable=True)

    # 设置级联和关系加载
    pixiv_tag_to_illusts_back_pixiv_illusts = relationship(Pixiv, back_populates='pixiv_illusts_pixiv_tag_to_illusts',
                                                           lazy='joined', innerjoin=True)
    pixiv_tag_to_illusts_back_pixiv_tag = relationship(PixivTag, back_populates='pixiv_tag_pixiv_tag_to_illusts',
                                                       lazy='joined', innerjoin=True)

    def __init__(self, illust_id, tag_id, created_at=None, updated_at=None):
        self.illust_id = illust_id
        self.tag_id = tag_id
        self.created_at = created_at
        self.updated_at = updated_at

    def __repr__(self):
        return f"<PixivT2I(illust_id='{self.illust_id}', tag_id='{self.tag_id}', " \
               f"created_at='{self.created_at}', updated_at='{self.updated_at}')>"


# Pixivision表
class Pixivision(Base):
    __tablename__ = f'{TABLE_PREFIX}pixivision_article'
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
        return f"<Pixivision(aid='{self.aid}', title='{self.title}', description='{self.description}', " \
               f"tags='{self.tags}', illust_id='{self.illust_id}', url='{self.url}', " \
               f"created_at='{self.created_at}', updated_at='{self.updated_at}')>"


# 冷却事件表
class CoolDownEvent(Base):
    __tablename__ = f'{TABLE_PREFIX}cool_down_event'
    __table_args__ = {'mysql_engine': 'InnoDB', 'mysql_charset': 'utf8mb4'}

    # 表结构
    id = Column(Integer, Sequence('cool_down_event_id_seq'),
                primary_key=True, nullable=False, index=True, unique=True)
    event_type = Column(String(16), nullable=False, index=True, comment='冷却事件类型/global/plugin/group/user')
    stop_at = Column(DateTime, nullable=False, comment='冷却结束时间')
    plugin = Column(String(64), nullable=True, index=True, comment='plugin事件对应插件名')
    group_id = Column(BigInteger, nullable=True, index=True, comment='group事件对应group_id')
    user_id = Column(BigInteger, nullable=True, index=True, comment='user事件对应user_id')
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
        return f"<CoolDownEvent(event_type='{self.event_type}', stop_at='{self.stop_at}', plugin='{self.plugin}'," \
               f"group_id='{self.group_id}', user_id='{self.user_id}', description='{self.description}', " \
               f"created_at='{self.created_at}', updated_at='{self.updated_at}')>"
