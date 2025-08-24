"""
# -*- coding: utf-8 -*-
@File    : app.py
@Author  : admin1
@Date    : 2025/8/21 12:35
@Description : web界面实现
"""
import os

from flask import Flask, render_template, request, url_for, redirect, flash
from werkzeug.utils import secure_filename

from data.import_questions import import_from_csv
from src.trainer import InterviewTrainer

app = Flask(__name__)
# app.secret_key = 'random_string_haha' # 持久化（生产环境）
app.secret_key = os.urandom(24) # 随机，开发环境

# 配置上传文件夹
UPLOAD_FOLDER = 'uploads'
ALLOWED_EXTENSIONS = {'csv'}
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER


def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


@app.route("/")
def index():
    """首页显示题目"""
    trainer = InterviewTrainer()
    question_data = trainer.get_next_question()
    trainer.close()
    if not question_data:
        return render_template("done.html")
    return render_template("question.html", q=question_data)


@app.route("/submit", methods=["POST"])
def submit():
    """提交答案并保存自评分"""
    trainer = InterviewTrainer()
    q_id = int(request.form["question_id"])
    user_answer = request.form["user_answer"].strip()
    rating = int(request.form["rating"])
    trainer.submit_answer(q_id, user_answer, rating)
    trainer.close()
    flash('答案已提交！')
    return redirect(url_for("index"))


@app.route("/stats")
def stats():
    """显示统计信息"""
    trainer = InterviewTrainer()
    stats = trainer.get_overall_stats()
    trainer.close()
    return render_template("stats.html", stats=stats)


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
