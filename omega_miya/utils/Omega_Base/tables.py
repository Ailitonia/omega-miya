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
    id = Column(Integer, Sequence('users_id_seq'), primary_key=True, nullable=False)
    qq = Column(BigInteger, nullable=False, comment='QQ号')
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

    id = Column(Integer, Sequence('skills_id_seq'), primary_key=True, nullable=False)
    name = Column(String(64), nullable=False, comment='技能名称')
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

    id = Column(Integer, Sequence('users_skills_id_seq'), primary_key=True, nullable=False)
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

    id = Column(Integer, Sequence('groups_id_seq'), primary_key=True, nullable=False)
    name = Column(String(64), nullable=False, comment='qq群名称')
    group_id = Column(Integer, nullable=False, comment='qq群号')
    notice_permissions = Column(Integer, nullable=False, comment='通知权限')
    command_permissions = Column(Integer, nullable=False, comment='命令权限')
    permission_level = Column(Integer, nullable=False, comment='权限等级, 越大越高')
    created_at = Column(DateTime, nullable=True)
    updated_at = Column(DateTime, nullable=True)

    avaiable_groups = relationship('UserGroup', back_populates='groups_have_users',
                                   cascade="all, delete", passive_deletes=True)
    sub_what = relationship('GroupSub', back_populates='groups_sub',
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

    id = Column(Integer, Sequence('users_groups_id_seq'), primary_key=True, nullable=False)
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


# 记录表
class History(Base):
    __tablename__ = 'history'
    __table_args__ = {'mysql_engine': 'InnoDB', 'mysql_charset': 'utf8mb4'}

    # 表结构
    id = Column(Integer, Sequence('history_id_seq'), primary_key=True, nullable=False)
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

    id = Column(Integer, Sequence('subscription_id_seq'), primary_key=True, nullable=False)
    # 订阅类型, 0暂留, 1直播间, 2动态, 8Pixivsion
    sub_type = Column(Integer, nullable=False, comment='订阅类型，0暂留，1直播间，2动态')
    sub_id = Column(Integer, nullable=False, comment='订阅id，直播为直播间房间号，动态为用户uid')
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

    id = Column(Integer, Sequence('groups_subs_id_seq'), primary_key=True, nullable=False)
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
    id = Column(Integer, Sequence('bili_dynamics_id_seq'), primary_key=True, nullable=False)
    uid = Column(Integer, nullable=False, comment='up的uid')
    dynamic_id = Column(BigInteger, nullable=False, comment='动态的id')
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

    id = Column(Integer, Sequence('vocations_id_seq'), primary_key=True, nullable=False)
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

    id = Column(Integer, Sequence('pixiv_tag_id_seq'), primary_key=True, nullable=False)
    tagname = Column(String(256), nullable=False, comment='tag名称')
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
    id = Column(Integer, Sequence('upixiv_illusts_id_seq'), primary_key=True, nullable=False)
    pid = Column(Integer, nullable=False, comment='pid')
    uid = Column(Integer, nullable=False, comment='uid')
    title = Column(String(512), nullable=False, comment='title')
    uname = Column(String(256), nullable=False, comment='author')
    tags = Column(String(2048), nullable=False, comment='tags')
    url = Column(String(2048), nullable=False, comment='url')
    created_at = Column(DateTime, nullable=True)
    updated_at = Column(DateTime, nullable=True)

    has_tags = relationship('PixivT2I', back_populates='illust_tags',
                            cascade="all, delete", passive_deletes=True)

    def __init__(self, pid, uid, title, uname, tags, url, created_at=None, updated_at=None):
        self.pid = pid
        self.uid = uid
        self.title = title
        self.uname = uname
        self.tags = tags
        self.url = url
        self.created_at = created_at
        self.updated_at = updated_at

    def __repr__(self):
        return "<Pixiv(pid='%s',uid='%s',title='%s',uname='%s'," \
               "tags='%s', url='%s', created_at='%s', created_at='%s')>" % (
                   self.pid, self.uid, self.title, self.uname,
                   self.tags, self.url, self.created_at, self.updated_at)


# Pixiv作品-tag表
class PixivT2I(Base):
    __tablename__ = 'pixiv_tag_to_illusts'
    __table_args__ = {'mysql_engine': 'InnoDB', 'mysql_charset': 'utf8mb4'}

    id = Column(Integer, Sequence('pixiv_tag_to_illusts_id_seq'), primary_key=True, nullable=False)
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


# Pixivsion表
class Pixivsion(Base):
    __tablename__ = 'pixivsion_article'
    __table_args__ = {'mysql_engine': 'InnoDB', 'mysql_charset': 'utf8mb4'}

    # 表结构
    id = Column(Integer, Sequence('pixivsion_article_id_seq'), primary_key=True, nullable=False)
    aid = Column(Integer, nullable=False, comment='aid')
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
        return "<Pixiv(aid='%s',title='%s',description='%s'," \
               "tags='%s', illust_id='%s', url='%s', created_at='%s', created_at='%s')>" % (
                   self.aid, self.title, self.description,
                   self.tags, self.illust_id, self.url, self.created_at, self.updated_at)
