"""
# -*- coding: utf-8 -*-
@File    : app.py
@Author  : admin1
@Date    : 2025/8/21 12:35
@Description : web界面实现
"""
import os

from flask import Flask, render_template, request, url_for, redirect, flash
from pymysql.cursors import DictCursor
from werkzeug.utils import secure_filename
from werkzeug.security import generate_password_hash, check_password_hash
from functools import wraps
from flask import session, g
from data.import_questions import import_from_csv
from src.trainer import InterviewTrainer

app = Flask(__name__)
# app.secret_key = 'random_string_haha' # 持久化（生产环境）
app.secret_key = os.urandom(24)  # 随机，开发环境

# 配置上传文件夹
UPLOAD_FOLDER = 'uploads'
ALLOWED_EXTENSIONS = {'csv'}
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER


def login_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if not session.get('user_id'):
            flash("请先登录")
            return redirect(url_for('login', next=request.path))
        return f(*args, **kwargs)

    return decorated


# 每次请求吧用户信息加载到g(便于模板使用)
@app.before_request
def load_current_user():
    g.user = None
    user_id = session.get('user_id')
    username = session.get('username')
    if user_id and username:
        g.user = {'id': user_id, 'username': username}


def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


@app.route("/")
@login_required
def index():
    """首页显示题目"""
    trainer = InterviewTrainer()
    question_data = trainer.get_next_question()
    trainer.close()
    if not question_data:
        return render_template("done.html")
    return render_template("question.html", q=question_data)


@app.route("/submit", methods=["POST"])
@login_required
def submit():
    """提交答案并保存自评分"""
    trainer = InterviewTrainer()
    try:
        q_id = int(request.form["question_id"])
        user_answer = request.form["user_answer"].strip()
        rating = int(request.form["rating"])
        user_id = session.get('user_id')  # 当前登录用户id
        duration = request.form.get('duration', None)
        duration_seconds = int(duration) if duration and duration.isdigit() else None
        record_id = trainer.submit_answer(q_id, user_answer, rating, user_id=user_id, duration_seconds=duration_seconds)
    finally:
        trainer.close()
    if record_id:
        # 跳转到 review 页面显示题目、参考答案、用户答案、评分与用时
        return redirect(url_for('review', record_id=record_id))
    else:
        flash('提交失败，请重试！')
        return redirect(url_for("index"))


@app.route("/review/<int:record_id>")
@login_required
def review(record_id):
    """显示提交后的问题对比，用户答案VS参考答案"""
    trainer = InterviewTrainer()
    try:
        # 从review_record取记录并 join question显示完整信息
        db = trainer.db
        cursor = db.conn.cursor(DictCursor)
        cursor.execute('''
            SELECT r.id as record_id, r.user_answer, r.rating, r.duration_seconds, r.reviewed_at,
                q.id as question_id, q.question, q.answer, q.category, q.difficulty
            FROM review_records r
            JOIN questions q ON r.question_id = q.id
            WHERE r.id = %s AND (r.user_id = %s AND r.user_id IS NULL)
        ''', (record_id, session.get('user_id')))
        row = cursor.fetchone()
    finally:
        trainer.close()
    if not row:
        flash("记录不存在或无权限查看")
        return redirect(url_for('index'))
    return render_template('review.html', rec=row)


@app.route("/stats")
@login_required
def stats():
    """显示统计信息"""
    trainer = InterviewTrainer()
    user_id = session.get('user_id')
    stats = trainer.get_overall_stats(user_id=user_id)
    trainer.close()
    return render_template("stats.html", stats=stats)


@app.route("/register", methods=['GET', 'POST'])
def register():
    """注册新用户"""
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "").strip()
        password2 = request.form.get("password2", "").strip()
        if not username or not password:
            flash("用户名和密码不能为空")
            return redirect(url_for('register'))
        if password != password2:
            flash("两次输入密码不一致")
            return redirect(url_for('register'))
        trainer = InterviewTrainer()
        created = trainer.db.create_user(username, password)
        trainer.close()
        if created:
            flash("注册成功，请登录")
            return redirect(url_for('login'))
        else:
            flash("用户名已存在或创建失败")
            return redirect('register')
    return render_template("register.html")


@app.route("/login", methods=['GET', 'POST'])
def login():
    """用户登录"""
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "").strip()
        if not username or not password:
            flash("用户名或密码不能为空")
            return redirect(url_for('login'))
        trainer = InterviewTrainer()
        user = trainer.db.verify_user(username, password)
        trainer.close()
        if user:
            session['user_id'] = user['id']
            session['username'] = user['username']
            flash(f"登录成功，欢迎 {user['username']}")
            next_url = request.args.get('next') or url_for('index')
            return redirect(next_url)
        else:
            flash("用户名或密码错误")
            return redirect(url_for('login'))
    return render_template("login.html")


@app.route("/logout")
def logout():
    session.clear()
    flash("已退出")
    return redirect(url_for('login'))


@app.route("/add_question", methods=["GET", "POST"])
def add_question():
    """添加题目"""
    if request.method == "POST":
        question = request.form['question'].strip()
        answer = request.form['answer'].strip()
        category = request.form['category'].strip()
        difficulty = request.form['difficulty'].strip()
        if not question:
            flash("问题不能为空！")
            return redirect(url_for('add_question'))
        trainer = InterviewTrainer()
        if trainer.question_exists(question):
            flash("题目已存在！")
            trainer.close()
            return redirect(url_for('add_question'))
        trainer.add_question(question, answer, category, difficulty)
        trainer.close()
        flash("题目添加完成！")
        return redirect(request.url)
    return render_template('add_question.html')


@app.route('/import_csv', methods=['GET', 'POST'])
def import_csv():
    """导入csv"""
    if request.method == 'POST':
        if 'file' not in request.files:
            flash("没有文件")
            return redirect(request.url)
        file = request.files['file']
        if file.filename == '':
            flash("未选择文件")
            return redirect(request.url)
        if file and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
            filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            file.save(filepath)
            result = import_from_csv(filepath, mode="web")
            if 'error' in result:
                flash(f"导入错误：{result['error']}")
            else:
                flash(f"导入完成：新增 {result['imported']} 题，跳过 {result['skipped']} 重复，失败 {result['failed']} 行")
            return redirect(url_for('index'))
        else:
            flash("只支持csv文件")
            return redirect(request.url)
    return render_template("import_csv.html")


if __name__ == '__main__':
    app.run(host="0.0.0.0", port=5000, debug=True)
