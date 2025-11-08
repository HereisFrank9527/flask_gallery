from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify, session, send_from_directory, abort
from app.models import db, Image, Tag, Like, Announcement, SiteSettings
from app.utils import allowed_file, create_thumbnail, get_client_ip
from werkzeug.utils import secure_filename
from werkzeug.security import check_password_hash, generate_password_hash
import os
from flask import current_app
from functools import wraps
from urllib.parse import urlparse

main_bp = Blueprint('main', __name__)
admin_bp = Blueprint('admin', __name__, url_prefix='/admin')


# 登录装饰器
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not session.get('admin_logged_in'):
            flash('请先登录', 'error')
            # 直接使用相对���径重定向，避免域名问题
            return redirect('/admin/login')
        return f(*args, **kwargs)
    return decorated_function


# 防盗链检查函数
def check_referer():
    """检查Referer是否在允许的域名列表中"""
    if not current_app.config.get('ENABLE_HOTLINK_PROTECTION', False):
        return True

    referer = request.headers.get('Referer')

    # 如果没有Referer（直接访问），允许
    if not referer:
        return True

    # 解析Referer的域名
    parsed = urlparse(referer)
    referer_host = parsed.netloc.split(':')[0]  # 移除端口号

    # 检查是否在允许列表中
    allowed_domains = current_app.config.get('ALLOWED_DOMAINS', [])
    for domain in allowed_domains:
        if referer_host == domain or referer_host.endswith('.' + domain):
            return True

    return False


# ==================== 前台路由 ====================

@main_bp.route('/')
def index():
    """首页 - 显示公告"""
    # 获取公告（只有一条记录，id=1）
    announcement = Announcement.query.first()
    if not announcement:
        # 如果没有公告，创建一个默认的
        announcement = Announcement(content='# 欢迎来到壁纸分享平台\n\n这里是公告内容，支持Markdown格式。\n\n请在管理后台修改公告内容。')
        db.session.add(announcement)
        db.session.commit()

    return render_template('index.html',
                         announcement=announcement,
                         title='首页')


@main_bp.route('/gallery')
def gallery():
    """画廊页面 - 无限滚动随机显示"""
    # 初始加载24张图片（两屏的量）
    initial_count = 24

    # 为每个会话生成随机种子
    if 'gallery_seed' not in session:
        import random
        session['gallery_seed'] = random.randint(1, 1000000)

    # 使用随机排序获取初始图片
    from sqlalchemy import func
    images = Image.query.order_by(func.random()).limit(initial_count).all()

    return render_template('gallery.html',
                         images=images,
                         title='画廊')


@main_bp.route('/filter')
def filter_images():
    """筛选页面 - 根据标签筛选图片，支持排序"""
    page = request.args.get('page', 1, type=int)
    tag_ids = request.args.getlist('tags', type=int)
    sort_by = request.args.get('sort', 'date')  # date, views, likes
    per_page = current_app.config['IMAGES_PER_PAGE']

    # 获取所有标签供筛选使用
    all_tags = Tag.query.order_by(Tag.name).all()

    # 如果选择了标签，进行筛选
    if tag_ids:
        query = Image.query.join(Image.tags).filter(Tag.id.in_(tag_ids))
    else:
        query = Image.query

    # 根据排序方式排序
    if sort_by == 'views':
        query = query.order_by(Image.views.desc())
    elif sort_by == 'likes':
        # 按点赞数排序需要子查询
        from sqlalchemy import func, select
        like_count = select(func.count(Like.id)).where(Like.image_id == Image.id).correlate(Image).scalar_subquery()
        query = query.order_by(like_count.desc())
    else:  # date
        query = query.order_by(Image.upload_date.desc())

    pagination = query.paginate(
        page=page, per_page=per_page, error_out=False
    )

    return render_template('filter.html',
                         images=pagination.items,
                         pagination=pagination,
                         all_tags=all_tags,
                         selected_tags=tag_ids,
                         sort_by=sort_by,
                         title='筛选')


@main_bp.route('/image/<int:image_id>')
def image_detail(image_id):
    """图片详情页"""
    image = Image.query.get_or_404(image_id)
    
    # 增加浏览次数
    image.views += 1
    db.session.commit()
    
    # 检查当前用户是否已点赞
    client_ip = get_client_ip(request)
    has_liked = Like.query.filter_by(image_id=image_id, ip_address=client_ip).first() is not None
    
    return render_template('image_detail.html', 
                         image=image,
                         has_liked=has_liked,
                         title=image.title or '图片详情')



@main_bp.route('/api/like/<int:image_id>', methods=['POST'])
def like_image(image_id):
    """点赞图片API"""
    image = Image.query.get_or_404(image_id)
    client_ip = get_client_ip(request)

    # 检查是否已点赞
    existing_like = Like.query.filter_by(image_id=image_id, ip_address=client_ip).first()

    if existing_like:
        # 取消点赞
        db.session.delete(existing_like)
        db.session.commit()
        return jsonify({'success': True, 'liked': False, 'like_count': image.like_count})
    else:
        # 添加点赞
        new_like = Like(image_id=image_id, ip_address=client_ip)
        db.session.add(new_like)
        db.session.commit()
        return jsonify({'success': True, 'liked': True, 'like_count': image.like_count})


# ==================== 图片访问路由（带防盗链保护） ====================

@main_bp.route('/uploads/<path:filename>')
def serve_upload(filename):
    """提供原图访问（带防盗链保护）"""
    if not check_referer():
        abort(403)  # 禁止访问
    return send_from_directory(current_app.config['UPLOAD_FOLDER'], filename)


@main_bp.route('/thumbnails/<path:filename>')
def serve_thumbnail(filename):
    """提供缩略图访问（带防盗链保护）"""
    if not check_referer():
        abort(403)  # 禁止访问
    return send_from_directory(current_app.config['THUMBNAIL_FOLDER'], filename)


# ==================== 管理后台路由 ====================

@admin_bp.route('/login', methods=['GET', 'POST'])
def login():
    """管理员登录"""
    if session.get('admin_logged_in'):
        return redirect(url_for('admin.dashboard'))

    if request.method == 'POST':
        password = request.form.get('password', '')

        if check_password_hash(current_app.config['ADMIN_PASSWORD_HASH'], password):
            session['admin_logged_in'] = True
            flash('登录成功！', 'success')
            return redirect(url_for('admin.dashboard'))
        else:
            flash('密码错误！', 'error')

    return render_template('admin/login.html')


@admin_bp.route('/logout')
def logout():
    """管理员登出"""
    session.pop('admin_logged_in', None)
    flash('已退出登录', 'success')
    return redirect(url_for('main.index'))


@admin_bp.route('/change-password', methods=['GET', 'POST'])
@login_required
def change_password():
    """修改管理员密码"""
    if request.method == 'POST':
        old_password = request.form.get('old_password', '')
        new_password = request.form.get('new_password', '')
        confirm_password = request.form.get('confirm_password', '')

        # 验证旧密码
        if not check_password_hash(current_app.config['ADMIN_PASSWORD_HASH'], old_password):
            flash('旧密码错误！', 'error')
            return redirect(request.url)

        # 验证新密码
        if len(new_password) < 6:
            flash('新密码长度至少6位！', 'error')
            return redirect(request.url)

        if new_password != confirm_password:
            flash('两次输入的新密码不一致！', 'error')
            return redirect(request.url)

        # 保存明文密码到配置文件
        config_path = os.path.join(os.path.dirname(__file__), 'config.py')
        with open(config_path, 'r', encoding='utf-8') as f:
            content = f.read()

        # 替换明文密码
        import re
        content = re.sub(
            r"ADMIN_PASSWORD = '[^']*'",
            f"ADMIN_PASSWORD = '{new_password}'",
            content
        )

        with open(config_path, 'w', encoding='utf-8') as f:
            f.write(content)

        # 更新当前配置
        current_app.config['ADMIN_PASSWORD'] = new_password
        current_app.config['ADMIN_PASSWORD_HASH'] = generate_password_hash(new_password)

        flash('密码修改成功！请妥善保管新密码。', 'success')
        return redirect(url_for('admin.dashboard'))

    return render_template('admin/change_password.html')


@admin_bp.route('/')
@login_required
def dashboard():
    """管理后台首页"""
    total_images = Image.query.count()
    total_tags = Tag.query.count()
    total_likes = Like.query.count()
    
    recent_images = Image.query.order_by(Image.upload_date.desc()).limit(5).all()
    
    return render_template('admin/dashboard.html',
                         total_images=total_images,
                         total_tags=total_tags,
                         total_likes=total_likes,
                         recent_images=recent_images)


@admin_bp.route('/images')
@login_required
def manage_images():
    """管理图片列表"""
    page = request.args.get('page', 1, type=int)
    per_page = 20
    
    pagination = Image.query.order_by(Image.upload_date.desc()).paginate(
        page=page, per_page=per_page, error_out=False
    )
    
    return render_template('admin/images.html',
                         images=pagination.items,
                         pagination=pagination)


@admin_bp.route('/upload', methods=['GET', 'POST'])
@login_required
def upload_image():
    """批量上传图片"""
    if request.method == 'POST':
        # 检查文件
        if 'files' not in request.files:
            flash('没有选择文件', 'error')
            return redirect(request.url)

        files = request.files.getlist('files')

        if not files or files[0].filename == '':
            flash('没有选择文件', 'error')
            return redirect(request.url)

        # 获取公共信息
        description = request.form.get('description', '')
        tag_names = request.form.get('tags', '').split(',')

        # 处理标签（提前创建，避免重复查询）
        tags = []
        for tag_name in tag_names:
            tag_name = tag_name.strip()
            if tag_name:
                tag = Tag.query.filter_by(name=tag_name).first()
                if not tag:
                    tag = Tag(name=tag_name)
                    db.session.add(tag)
                tags.append(tag)

        # 批量处理文件
        from datetime import datetime
        success_count = 0
        error_count = 0

        for file in files:
            if file and file.filename and allowed_file(file.filename):
                try:
                    # 保存原图
                    filename = secure_filename(file.filename)
                    # 添加时间戳和随机数避免文件名冲突
                    import random
                    timestamp = datetime.now().strftime('%Y%m%d%H%M%S')
                    random_num = random.randint(1000, 9999)
                    name, ext = os.path.splitext(filename)
                    filename = f"{name}_{timestamp}_{random_num}{ext}"

                    filepath = os.path.join(current_app.config['UPLOAD_FOLDER'], filename)
                    file.save(filepath)

                    # 创建缩略图
                    thumbnail_filename = f"thumb_{filename}"
                    thumbnail_path = os.path.join(current_app.config['THUMBNAIL_FOLDER'], thumbnail_filename)
                    create_thumbnail(filepath, thumbnail_path, current_app.config['THUMBNAIL_SIZE'])

                    # 保存到数据库
                    new_image = Image(
                        filename=filename,
                        thumbnail=thumbnail_filename,
                        title='',  # 批量上传不设置标题
                        description=description
                    )

                    # 添加标签
                    for tag in tags:
                        new_image.tags.append(tag)

                    db.session.add(new_image)
                    success_count += 1
                except Exception as e:
                    error_count += 1
                    print(f"Error uploading {file.filename}: {e}")
            else:
                error_count += 1

        # 提交所有更改
        db.session.commit()

        if success_count > 0:
            flash(f'成功上传 {success_count} 张图片！', 'success')
        if error_count > 0:
            flash(f'{error_count} 张图片上传失败', 'error')

        return redirect(url_for('admin.manage_images'))

    return render_template('admin/upload.html')


@admin_bp.route('/image/<int:image_id>/edit', methods=['GET', 'POST'])
@login_required
def edit_image(image_id):
    """编辑图片信息"""
    image = Image.query.get_or_404(image_id)
    
    if request.method == 'POST':
        image.title = request.form.get('title', '')
        image.description = request.form.get('description', '')
        
        # 更新标签
        image.tags.clear()
        tag_names = request.form.get('tags', '').split(',')
        for tag_name in tag_names:
            tag_name = tag_name.strip()
            if tag_name:
                tag = Tag.query.filter_by(name=tag_name).first()
                if not tag:
                    tag = Tag(name=tag_name)
                    db.session.add(tag)
                image.tags.append(tag)
        
        db.session.commit()
        flash('图片信息更新成功！', 'success')
        return redirect(url_for('admin.manage_images'))
    
    # 获取当前图片的标签名称
    current_tags = ','.join([tag.name for tag in image.tags])
    
    return render_template('admin/edit_image.html', image=image, current_tags=current_tags)


@admin_bp.route('/image/<int:image_id>/delete', methods=['POST'])
@login_required
def delete_image(image_id):
    """删除单张图片"""
    image = Image.query.get_or_404(image_id)

    # 删除文件
    try:
        os.remove(os.path.join(current_app.config['UPLOAD_FOLDER'], image.filename))
        os.remove(os.path.join(current_app.config['THUMBNAIL_FOLDER'], image.thumbnail))
    except:
        pass

    # 删除数据库记录
    db.session.delete(image)
    db.session.commit()

    flash('图片删除成功！', 'success')
    return redirect(url_for('admin.manage_images'))


@admin_bp.route('/images/batch-delete', methods=['POST'])
@login_required
def batch_delete_images():
    """批量删除图片"""
    image_ids = request.form.getlist('image_ids', type=int)

    if not image_ids:
        flash('请选择要删除的图片', 'error')
        return redirect(url_for('admin.manage_images'))

    deleted_count = 0
    for image_id in image_ids:
        image = Image.query.get(image_id)
        if image:
            # 删除文件
            try:
                os.remove(os.path.join(current_app.config['UPLOAD_FOLDER'], image.filename))
                os.remove(os.path.join(current_app.config['THUMBNAIL_FOLDER'], image.thumbnail))
            except:
                pass

            # 删除数据库记录
            db.session.delete(image)
            deleted_count += 1

    db.session.commit()
    flash(f'成功删除 {deleted_count} 张图片！', 'success')
    return redirect(url_for('admin.manage_images'))


@admin_bp.route('/tags')
@login_required
def manage_tags():
    """管理标签"""
    tags = Tag.query.order_by(Tag.name).all()
    return render_template('admin/tags.html', tags=tags)


@admin_bp.route('/tag/<int:tag_id>/delete', methods=['POST'])
@login_required
def delete_tag(tag_id):
    """删除标签"""
    tag = Tag.query.get_or_404(tag_id)
    db.session.delete(tag)
    db.session.commit()
    flash('标签删除成功！', 'success')
    return redirect(url_for('admin.manage_tags'))


@admin_bp.route('/announcement', methods=['GET', 'POST'])
@login_required
def manage_announcement():
    """管理公告"""
    announcement = Announcement.query.first()
    if not announcement:
        announcement = Announcement(content='')
        db.session.add(announcement)
        db.session.commit()

    if request.method == 'POST':
        content = request.form.get('content', '')
        announcement.content = content
        db.session.commit()
        flash('公告更新成功！', 'success')
        return redirect(url_for('admin.manage_announcement'))

    return render_template('admin/announcement.html', announcement=announcement)


@admin_bp.route('/hotlink', methods=['GET', 'POST'])
@login_required
def manage_hotlink():
    """管理防盗链设置"""
    if request.method == 'POST':
        enable = request.form.get('enable') == 'on'
        domains = request.form.get('domains', '').strip()

        # 读取配置文件
        config_path = os.path.join(os.path.dirname(__file__), 'config.py')
        with open(config_path, 'r', encoding='utf-8') as f:
            content = f.read()

        # 替换防盗链开关
        import re
        content = re.sub(
            r'ENABLE_HOTLINK_PROTECTION = (True|False)',
            f'ENABLE_HOTLINK_PROTECTION = {enable}',
            content
        )

        # 处理域名列表
        domain_list = [d.strip() for d in domains.split('\n') if d.strip()]
        domains_str = ',\n        '.join([f"'{d}'" for d in domain_list])
        content = re.sub(
            r'ALLOWED_DOMAINS = \[[^\]]*\]',
            f'ALLOWED_DOMAINS = [\n        {domains_str}\n    ]',
            content,
            flags=re.DOTALL
        )

        with open(config_path, 'w', encoding='utf-8') as f:
            f.write(content)

        # 更新当前配置
        current_app.config['ENABLE_HOTLINK_PROTECTION'] = enable
        current_app.config['ALLOWED_DOMAINS'] = domain_list

        flash('防盗链设置已更新！重启应用后生效。', 'success')
        return redirect(url_for('admin.manage_hotlink'))

    # 获取当前配置
    enable = current_app.config.get('ENABLE_HOTLINK_PROTECTION', True)
    domains = '\n'.join(current_app.config.get('ALLOWED_DOMAINS', []))

    return render_template('admin/hotlink.html', enable=enable, domains=domains)

@admin_bp.route('/site-settings', methods=['GET', 'POST'])
@login_required
def manage_site_settings():
    """管理网站设置"""
    from app import cache

    settings = SiteSettings.query.first()
    if not settings:
        settings = SiteSettings()
        db.session.add(settings)
        db.session.commit()

    if request.method == 'POST':
        settings.site_title = request.form.get('site_title', '壁纸分享平台')
        settings.welcome_message = request.form.get('welcome_message', '欢迎来到壁纸分享平台')
        db.session.commit()

        # 清除缓存
        cache.clear()

        flash('网站设置已更新！', 'success')
        return redirect(url_for('admin.manage_site_settings'))

    return render_template('admin/site_settings.html', settings=settings)


@main_bp.route('/api/gallery/load-more')
def gallery_load_more():
    """画廊无限滚动加载更多图片API"""
    offset = request.args.get('offset', 0, type=int)
    limit = request.args.get('limit', 12, type=int)
    
    # 获取所有图片ID并随机排序（使用固定种子保证会话内一致性）
    from flask import session
    if 'gallery_seed' not in session:
        import random
        session['gallery_seed'] = random.randint(1, 1000000)
    
    # 使用会话种子进行随机排序
    from sqlalchemy import func
    all_images = Image.query.order_by(func.random()).all()
    
    # 获取指定范围的图片
    images = all_images[offset:offset + limit]
    
    # 转换为JSON格式
    result = []
    for image in images:
        result.append({
            'id': image.id,
            'thumbnail': url_for('main.serve_thumbnail', filename=image.thumbnail),
            'title': image.title or '',
            'views': image.views,
            'likes': image.like_count,
            'tags': [{'name': tag.name} for tag in image.tags],
            'detail_url': url_for('main.image_detail', image_id=image.id)
        })
    
    return jsonify({
        'images': result,
        'has_more': offset + limit < len(all_images)
    })
