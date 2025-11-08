from datetime import datetime
from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()

# 图片和标签的多对多关系表
image_tags = db.Table('image_tags',
    db.Column('image_id', db.Integer, db.ForeignKey('image.id'), primary_key=True),
    db.Column('tag_id', db.Integer, db.ForeignKey('tag.id'), primary_key=True)
)


class Image(db.Model):
    """图片模型"""
    id = db.Column(db.Integer, primary_key=True)
    filename = db.Column(db.String(255), nullable=False)
    thumbnail = db.Column(db.String(255), nullable=False)
    title = db.Column(db.String(200))
    description = db.Column(db.Text)
    upload_date = db.Column(db.DateTime, default=datetime.utcnow)
    views = db.Column(db.Integer, default=0)
    
    # 关系
    tags = db.relationship('Tag', secondary=image_tags, backref=db.backref('images', lazy='dynamic'))
    likes = db.relationship('Like', backref='image', lazy='dynamic', cascade='all, delete-orphan')
    
    @property
    def like_count(self):
        """获取点赞数"""
        return self.likes.count()
    
    def __repr__(self):
        return f'<Image {self.filename}>'


class Tag(db.Model):
    """标签模型"""
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), unique=True, nullable=False)
    
    def __repr__(self):
        return f'<Tag {self.name}>'


class Like(db.Model):
    """点赞模型"""
    id = db.Column(db.Integer, primary_key=True)
    image_id = db.Column(db.Integer, db.ForeignKey('image.id'), nullable=False)
    ip_address = db.Column(db.String(50), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # 确保同一IP对同一图片只能点赞一次
    __table_args__ = (db.UniqueConstraint('image_id', 'ip_address', name='unique_like'),)

    def __repr__(self):
        return f'<Like image_id={self.image_id} ip={self.ip_address}>'


class Announcement(db.Model):
    """公告模型"""
    id = db.Column(db.Integer, primary_key=True)
    content = db.Column(db.Text, nullable=False, default='')
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def __repr__(self):
        return f'<Announcement {self.id}>'


class SiteSettings(db.Model):
    """网站设置模型"""
    id = db.Column(db.Integer, primary_key=True)
    site_title = db.Column(db.String(100), default='壁纸分享平台')
    welcome_message = db.Column(db.String(200), default='欢迎来到壁纸分享平台')
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def __repr__(self):
        return f'<SiteSettings {self.id}>'
