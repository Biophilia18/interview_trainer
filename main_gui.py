"""
# -*- coding: utf-8 -*-
@File    : main_gui.py
@Author  : admin1
@Date    : 2025/8/25 16:48
@Description : GUI实现
"""
import json
import logging
import logging.handlers
import platform

import customtkinter as ctk
import tkinter as tk
import os
from tkinter import messagebox, filedialog
from datetime import datetime
from pymysql.cursors import DictCursor
from src.trainer import InterviewTrainer
from data.import_questions import import_from_csv


def setup_logging():
    """配置日志记录系统"""
    # 创建日志目录
    log_dir = "logs"
    os.makedirs(log_dir, exist_ok=True)

    # 创建日志文件名（按日期）
    log_file = os.path.join(log_dir, f"interview_trainer_{datetime.now().strftime('%Y%m%d')}.log")

    # 创建日志记录器
    logger = logging.getLogger("InterviewTrainerGUI")
    logger.setLevel(logging.DEBUG)

    # 创建格式化器
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s -%(message)s'
    )

    # 文件处理器 - 按日期轮询，保留7天日志
    file_handler = logging.handlers.TimedRotatingFileHandler(
        log_file, when='midnight', interval=1, backupCount=7, encoding='utf-8'
    )
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(formatter)

    # 控制台处理器
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.DEBUG)
    console_handler.setFormatter(formatter)

    # 添加处理器到记录器
    logger.addHandler(file_handler)
    logger.addHandler(console_handler)

    return logger


# 获取日志记录器实例
logger = setup_logging()


class InterviewTrainerGUI:
    def __init__(self):
        """初始化应用"""
        logger.info("启动UI")
        # CTk基本设置
        # 设置主题
        ctk.set_appearance_mode("light")
        ctk.set_default_color_theme("blue")

        # 初始化应用
        self.app = ctk.CTk()
        self.app.title("面试自测训练器 v1.0.0")
        self.app.geometry("1000x800")

        # 设置应用关闭事件处理器
        self.app.protocol("WM_DELETE_WINDOW", self.on_closing)
        self.set_global_style()

        # 应用状态 当前用户信息
        self.current_user = None
        self.user_preferences = {}
        self.trainer = None
        self.current_question = None

        # 计时器相关
        self.timer_running = False
        self.elapsed_time = 0
        self.timer_job = None
        try:
            # 初始化数据库连接
            self.trainer = InterviewTrainer()
        except Exception as e:
            logger.exception("Trainer 初始化失败")
            messagebox.showerror("初始化失败", f"无法连接或加载数据层：：{str(e)}")
            raise
        # 构建 UI (分区函数)
        self.setup_auth_frame()  # 登录/注册
        self.setup_main_frame()  # 主框架(被隐藏直到登录)
        # 从本地 session.json 尝试恢复用户名
        self.load_saved_session()

    def set_global_style(self):
        """设置全局字体和主题"""
        # 判断系统，选择字体
        sys = platform.system()
        if sys == "Darwin":  # macOS
            family = "PingFang SC"
        elif sys == "Windows":
            family = "苹方-简"
        else:  # Linux 或其他
            family = "Noto Sans CJK SC"

        # 全局字体（默认字号大一点，现代感更强）
        default_font = ctk.CTkFont(family=family, size=15)
        # 全局标题字体
        self.title_font = ctk.CTkFont(family=family, size=20, weight="bold")
        self.textbox_font = ctk.CTkFont(family=family, size=16)

        self.app.option_add("*Font", default_font)

        # 主题（推荐 dark + blue）
        ctk.set_appearance_mode("Light")  # 可选: "Light", "Dark", "System"
        ctk.set_default_color_theme("blue")  # 可选: "blue", "green", "dark-blue"

    # --------------------
    # 认证区（登录/注册）
    # --------------------
    def setup_auth_frame(self):
        """登录注册界面"""
        self.auth_frame = ctk.CTkFrame(self.app)
        self.auth_frame.pack(fill='both', expand=True)

        # 登录表单
        title = ctk.CTkLabel(self.auth_frame, text="面试自测训练器", font=self.title_font)
        title.pack(pady=24)

        # 用户名 密码输入
        self.username_entry = ctk.CTkEntry(self.auth_frame, placeholder_text="用户名", font=self.textbox_font)
        self.username_entry.pack(fill='x', pady=10, padx=40)
        self.password_entry = ctk.CTkEntry(self.auth_frame, placeholder_text="密码", show="*")
        self.password_entry.pack(fill='x', pady=10, padx=40)

        # 记住我
        self.remember_var = tk.BooleanVar(value=False)
        self.remember_me = ctk.CTkCheckBox(self.auth_frame, text="记住我", variable=self.remember_var,
                                           font=self.textbox_font)
        self.remember_me.pack(pady=5)

        # 按钮区域
        button_frame = ctk.CTkFrame(self.auth_frame)
        button_frame.pack(pady=20)

        login_btn = ctk.CTkButton(button_frame, text="登录", width=120, command=self.handle_login,
                                  font=self.textbox_font)
        login_btn.pack(side="left", padx=10)

        register_btn = ctk.CTkButton(button_frame, text="注册", width=120, command=self.handle_register,
                                     font=self.textbox_font)
        register_btn.pack(side="left", padx=10)

        # 附加说明
        help_lbl = ctk.CTkLabel(self.auth_frame, text="没有账号？直接注册即可（用户名不可重复）", text_color="#6b7280",
                                font=self.textbox_font)
        help_lbl.pack(pady=6)

    def handle_login(self):
        """登录动作： 校验账号 -> 切换到主界面 -> 加载首题&偏好"""
        username = self.username_entry.get().strip()
        password = self.password_entry.get().strip()
        if not username or not password:
            messagebox.showwarning("输入错误", "用户名和密码不能为空")
            return
        try:
            user = self.trainer.db.verify_user(username, password)
            if not user:
                messagebox.showerror("登录失败", "用户名或密码输入错误")
                return
            # 登录成功
            self.current_user = user
            logger.info(f"用户登录：{user['username']}")
            if self.remember_var.get():
                self.save_session_temp(username, password)
            self.load_user_preferences()
            self.show_main_interface()
            # 立即加载题目
            self.load_next_question()
        except Exception as e:
            logger.exception("登录异常")
            messagebox.showerror("登录异常", f"登录失败：{e}")

    def handle_register(self):
        """注册动作： 弹窗获取并写入db"""
        username = self.username_entry.get().strip()
        password = self.password_entry.get().strip()
        if not username or not password:
            messagebox.showwarning("输入错误", "用户名和密码不能为空")
            return
        try:
            new_id = self.trainer.db.create_user(username, password)
            if new_id:
                messagebox.showinfo("注册成功", "注册成功！现在可以直接登录。")
                logger.info(f"新用户注册：{username}")
            else:
                messagebox.showerror("注册失败", "用户名可能已存在或创建失败")
        except Exception as e:
            logger.exception("注册异常")
            messagebox.showerror("注册异常", f"注册失败：{e}")

    # --------------------
    # 主界面与选项卡
    # --------------------
    def setup_main_frame(self):
        """主框架 包含tabview"""
        self.main_frame = ctk.CTkFrame(self.app)
        # 顶部工具条
        topbar = ctk.CTkFrame(self.main_frame)
        topbar.pack(fill='x', padx=12, pady=8)
        welcome = ctk.CTkLabel(topbar, text="欢迎使用自测工具", anchor="w", font=self.textbox_font)
        welcome.pack(side="left")

        logout_btn = ctk.CTkButton(topbar, text="登出", command=self.logout, width=90, font=self.textbox_font)
        logout_btn.pack(side="right", padx=6)

        # 创建选项卡视图
        self.tab_view = ctk.CTkTabview(self.main_frame, width=980)
        self.tab_view.pack(fill='both', expand=True, padx=20, pady=20)

        # tabs
        self.tab_view.add("自测")
        self.tab_view.add("回顾")
        self.tab_view.add("统计")
        self.tab_view.add("题库")
        self.tab_view.add("个人中心")

        # 分别设置每个tab的内容
        self.setup_practice_tab()
        self.setup_review_tab()
        self.setup_stats_tab()
        self.setup_question_bank_tab()
        self.setup_profile_tab()

    def show_main_interface(self):
        """隐藏登录认证界面，显示主界面"""
        try:
            self.auth_frame.pack_forget()
        except Exception:
            pass
        # 如果main_frame尚未pack，则pack
        if not getattr(self, "main_frame", None):
            self.setup_main_frame()
        self.main_frame.pack(fill='both', expand=True)

    # --------------------
    # 自测 Tab（题目显示、计时、提交）
    # --------------------
    def setup_practice_tab(self):
        """设置自测布局组件"""
        frame = self.tab_view.tab("自测")
        # 左右布局： 题目 + 控制
        top = ctk.CTkFrame(frame)
        top.pack(fill='both', expand=False, padx=12, pady=8)

        # 题目 meta
        self.meta_label = ctk.CTkLabel(top, text="(题目 meta)", anchor="w", font=self.textbox_font)
        self.meta_label.pack(fill='x', padx=6, pady=(2, 6))

        # 题目内容-只读
        self.question_textbox = ctk.CTkTextbox(top, height=120, font=self.textbox_font)
        self.question_textbox.pack(fill="x", padx=6, pady=(0, 8))
        self.question_textbox.configure(state='disabled')

        # 答案输入
        ans_lbl = ctk.CTkLabel(top, text="你的答案", anchor="w", font=self.textbox_font)
        ans_lbl.pack(fill="x", padx=6)
        self.answer_textbox = ctk.CTkTextbox(top, height=160, font=self.textbox_font)
        self.answer_textbox.pack(fill='both', padx=6, pady=(0, 8))

        # 参考答案区域(初始隐藏)
        self.answer_frame = ctk.CTkFrame(top)
        self.answer_label = ctk.CTkLabel(self.answer_frame, text="参考答案", anchor="w", font=self.textbox_font)
        self.answer_label.pack(fill="x", padx=6)
        self.ref_answer_textbox = ctk.CTkTextbox(self.answer_frame, height=200, font=self.textbox_font)
        self.ref_answer_textbox.pack(fill="x", padx=6, pady=(0, 8))
        self.ref_answer_textbox.configure(state="disabled")
        self.answer_frame.pack_forget()  # 初始隐藏
        # 控制行
        ctrl = ctk.CTkFrame(top)
        ctrl.pack(fill='x', padx=6, pady=6)

        # timer label
        self.timer_label = ctk.CTkLabel(ctrl, text="用时：0s", font=self.textbox_font)
        self.timer_label.pack(side="left", padx=10)

        # 评分选择
        self.rating_var = tk.StringVar(value="2")
        rating_box = ctk.CTkComboBox(ctrl, values=["1", "2", "3", "4", "5"],
                                     variable=self.rating_var, width=110, font=self.textbox_font)
        rating_box.pack(side="left", padx=10)

        # 答案
        self.show_answer_btn = ctk.CTkButton(ctrl, text="参考答案", command=self.show_reference_answer, width=90,
                                             font=self.textbox_font)
        self.show_answer_btn.pack(side="left", padx=6)

        # 按钮区域
        btn_frame = ctk.CTkFrame(ctrl)
        btn_frame.pack(side="right")
        self.pause_btn = ctk.CTkButton(btn_frame, text="暂停", command=self.toggle_pause, width=80,
                                       font=self.textbox_font, state="normal")
        self.pause_btn.pack(side="left", padx=6)
        self.submit_btn = ctk.CTkButton(btn_frame, text="提交", command=self.submit_answer, width=90,
                                        font=self.textbox_font, state="normal")
        self.submit_btn.pack(side="left", padx=6)
        self.next_btn = ctk.CTkButton(btn_frame, text="下一题", command=self.load_next_question, width=90,
                                      font=self.textbox_font)
        self.next_btn.pack(side="left", padx=6)
        # 是否暂停标记位
        self.is_paused = False

    def show_reference_answer(self):
        if not self.current_question:
            messagebox.showinfo("提示", "当前没有题目")
            return

        # 切换参考答案区域显示状态
        if self.answer_frame.winfo_ismapped():
            # 如果已经显示就隐藏
            self.answer_frame.pack_forget()
            self.show_answer_btn.configure(text="参考答案")
        else:  # 如果隐藏则显示并填充答案
            ans = self.current_question.get("answer") or "(无参考答案)"
            self.ref_answer_textbox.configure(state="normal")
            self.ref_answer_textbox.delete("1.0", "end")
            self.ref_answer_textbox.insert("end", ans)
            self.ref_answer_textbox.configure(state="disabled")
            self.answer_frame.pack(fill="x", padx=6, pady=(0, 8))
            self.show_answer_btn.configure(text="隐藏答案")

    def load_next_question(self):
        """从trainer获取下一题并显示，无题则提示"""
        try:
            # 停止当前问题的计时器
            self.reset_timer_state()
            self.stop_timer()

            # 隐藏参考答案区域（如果有显示）
            if self.answer_frame.winfo_ismapped():
                self.answer_frame.pack_forget()
                self.show_answer_btn.configure(text="参考答案")

            question = self.trainer.get_next_question()
            if not question:
                messagebox.showinfo("完成", "没有需要复习的题目了")
                # 清空显示
                self.display_question(None)
                return
            self.current_question = question
            self.display_question(question)
            # 开始计时
            self.reset_timer()
            self.start_timer()
        except Exception as e:
            logger.exception("加载下一题失败")
            messagebox.showerror("加载失败", f"加载下一题失败：{str(e)}")

    def display_question(self, q):
        """把题目信息填入UI"""
        # 清空答题区
        self.answer_textbox.delete("1.0", "end")
        if not q:
            self.question_textbox.configure(state="normal")
            self.question_textbox.delete("1.0", "end")
            self.question_textbox.insert("end", "(没有题目)")
            self.question_textbox.configure(state="disabled")
            self.question_textbox.configure(text="(无)")
        meta_text = f"[{q.get('category', '未分类')}] - [{q.get('difficulty', '中等')}] - [掌握程度: {q.get('level', 0)}/5]"
        self.meta_label.configure(text=meta_text)

        self.question_textbox.configure(state="normal")
        self.question_textbox.delete("1.0", "end")
        self.question_textbox.insert("end", q.get("question", "(空)"))
        self.question_textbox.configure(state="disabled")

    # 计时器 start stop reset 更新显示
    def start_timer(self):
        if self.timer_running:
            return
        self.timer_running = True
        self._tick_timer()

    def _tick_timer(self):
        if not self.timer_running:
            return
        self.elapsed_time += 1
        self.timer_label.configure(text=f"用时：{self.elapsed_time}s")
        # 用after注册下一次
        self.timer_job = self.app.after(1000, self._tick_timer)

    def stop_timer(self):
        self.timer_running = False  # 先设置状态，防止回调继续
        if self.timer_job:
            try:
                self.app.after_cancel(self.timer_job)
            except Exception:
                pass
        self.timer_running = False
        self.timer_job = None

    def reset_timer(self):
        self.stop_timer()
        self.elapsed_time = 0
        self.timer_label.configure(text="用时：0s")

    def toggle_pause(self):
        """切换暂停/继续状态 """
        if self.timer_running:
            self.stop_timer()
            self.pause_btn.configure(text="继续", fg_color="#FF9800")  # 橙色暂停
            self.is_paused = True
            # 禁用提交按钮
            self.submit_btn.configure(state="disabled")
            self.answer_textbox.configure(state='disabled')  # 禁用答题区
            # 显示提示信息
            messagebox.showinfo("已暂停", "答题已暂停，请点击'继续'按钮恢复")
        else:
            self.start_timer()
            self.pause_btn.configure(text="暂停", fg_color="#1F6AA5")  # 恢复原色
            self.is_paused = False

            # 启用提交按钮 - 确保在UI线程中执行
            self.app.after(100, lambda: self.submit_btn.configure(state="normal"))
            self.answer_textbox.configure(state="normal")

    def submit_answer(self):
        """读取用户答案与评分，提交给 trainer，保存记录并跳转下一题"""
        if self.is_paused:
            messagebox.showwarning("无法提交", "请先点击'继续'按钮恢复答题后再提交")
            return
        if not self.current_question:
            messagebox.showwarning("无题", "当前没有题目可以提交")
            return
        # 停止当前计时
        self.stop_timer()
        answer = self.answer_textbox.get("1.0", "end").strip()
        try:
            rating = int(self.rating_var.get())
        except Exception:
            rating = 2
        try:
            record_id = self.trainer.submit_answer(
                self.current_question['id'],
                answer,
                rating,
                user_id=self.current_user.get('id') if self.current_user else None,
                duration_seconds=self.elapsed_time
            )
            if record_id:
                logger.info(f"已提交记录 id={record_id}")
                # messagebox.showinfo("提交成功", "答案提交成功，进入下一题。")
                self.reset_timer_state()
                self.load_next_question()
            else:
                messagebox.showerror("提交失败", "提交未成功（请检查数据库或日志）")
        except Exception as e:
            logger.exception("提交异常")
            messagebox.showerror("提交失败", f"提交异常：{str(e)}")

    def reset_timer_state(self):
        self.is_paused = False
        self.pause_btn.configure(text="暂停")
        # 确保提交按钮状态正确
        self.app.after(100, lambda: self.submit_btn.configure(state="normal"))

    # --------------------
    # 回顾 Tab（查看历史答题记录）
    # --------------------
    def setup_review_tab(self):
        """实现回顾功能界面"""
        tab = self.tab_view.tab("回顾")
        # 左右： 列表 + 详情
        left = ctk.CTkFrame(tab)
        left.pack(side="left", fill="y", padx=8, pady=8)

        right = ctk.CTkFrame(tab)
        right.pack(side="right", fill="both", expand=True, padx=8, pady=8)

        ctk.CTkLabel(left, text="最近记录").pack(pady=6)
        self.review_listbox = tk.Listbox(left, width=36, font=self.textbox_font)
        self.review_listbox.pack(fill="y", expand=True, pady=6)
        self.review_listbox.bind("<<ListboxSelect>>", self.on_review_select)

        self.refresh_view_btn = ctk.CTkButton(left, text="刷新", command=self.refresh_reviews, font=self.textbox_font)
        self.refresh_view_btn.pack(pady=6)

        # 详情区
        ctk.CTkLabel(right, text="详情", font=self.textbox_font).pack(anchor="w", pady=(6, 0))
        self.review_detail = ctk.CTkTextbox(right, height=25, font=self.textbox_font)
        self.review_detail.pack(fill="both", expand=True, pady=6)
        self.review_detail.configure(state="disabled")

        # 初始加载
        self.review_cache = []
        self.refresh_reviews()

    def refresh_reviews(self):
        """从db拉取当前用户的最近记录（50）条"""
        self.review_listbox.delete(0, "end")
        self.review_cache = []
        try:
            db = self.trainer.db

            cursor = db.conn.cursor(DictCursor)
            if self.current_user:
                cursor.execute("""
                    SELECT r.id, r.question_id, r.user_answer, r.rating, r.duration_seconds, r.reviewed_at,
                        q.question AS question_text, q.answer AS answer_text
                    FROM review_records r
                    JOIN questions q ON r.question_id = q.id
                    WHERE r.user_id = %s
                    ORDER BY r.reviewed_at DESC
                    LIMIT 100
                """, (self.current_user['id'],))
            else:
                # messagebox.showwarning("未登录","无法获取记录")
                # return
                cursor.execute("""
                    SELECT r.id, r.question_id, r.user_answer, r.rating, r.duration_seconds, r.reviewed_at,
                        q.question AS question_text, q.answer AS answer_text
                    FROM review_records r
                    JOIN questions q ON r.question_id = q.id
                    ORDER BY r.reviewed_at DESC
                    LIMIT 50
                """)
            rows = cursor.fetchall()
            for row in rows:
                label = f"[{row['reviewed_at']}] [Q#{row['question_id']}] 评分：{row['rating']} "
                self.review_listbox.insert("end", label)
                self.review_cache.append(row)
        except Exception as e:
            logger.exception("加载回顾失败")
            messagebox.showerror("回顾加载失败", f"无法加载回顾记录：{e}")

    def on_review_select(self, event):
        sel = self.review_listbox.curselection()
        if not sel:
            return
        idx = sel[0]
        rec = self.review_cache[idx]
        #         txt = f"""问题(Q#{rec['question_id']}):
        # {rec.get('question_text', '(无)')}
        #
        # 你的答案:
        # {rec.get('user_answer')}
        #
        # 参考答案:
        # {rec.get('answer_text')}
        #
        # 掌握程度: [{rec.get('rating')}/5]
        # 用时: {rec.get('duration_seconds')}s
        # 提交时间: {rec.get('reviewed_at')}"""
        # 三重多引号的f-string第二行内容需要顶格书写
        txt = (f"问题(Q#{rec['question_id']}):\n"
               f"{rec.get('question_text', '(无)')}\n\n"
               f"你的答案:\n"
               f"{rec.get('user_answer')}\n\n"
               f"参考答案:\n"
               f"{rec.get('answer_text')}\n\n"
               f"掌握程度: [{rec.get('rating')}/5]\n"
               f"用时: {rec.get('duration_seconds')}s\n"
               f"提交时间: {rec.get('reviewed_at')}")
        # txt = f"问题（Q#{rec['question_id']}）:\n{rec.get('question_text', '(无)')}\n\n你的答案:\n{rec.get('user_answer')}\n\n参考答案:\n{rec.get('answer_text')}\n\n掌握程度: [{rec.get('rating')}/5]\n用时: {rec.get('duration_seconds')}s\n提交时间: {rec.get('reviewed_at')}"
        self.review_detail.configure(state="normal")
        self.review_detail.delete("1.0", "end")
        self.review_detail.insert("end", txt)
        self.review_detail.configure(state="disabled")

    # --------------------
    # 统计 Tab（文本 + 简单图表）
    # --------------------
    def setup_stats_tab(self):
        tab = self.tab_view.tab("统计")

        # 顶部按钮行
        top = ctk.CTkFrame(tab)
        top.pack(fill="x", padx=8, pady=8)

        self.stats_refresh_btn = ctk.CTkButton(top, text="刷新统计", command=self.refresh_stats, font=self.textbox_font)
        self.stats_refresh_btn.pack(side="left", padx=6)

        export_btn = ctk.CTkButton(top, text="导出统计 (JSON)", command=self.export_stats_json, font=self.textbox_font)
        export_btn.pack(side="left", padx=6)

        # 文本显示区域
        self.stats_text = ctk.CTkTextbox(tab, height=22, font=self.textbox_font)
        self.stats_text.pack(fill="both", expand=True, padx=8, pady=8)
        self.stats_text.configure(state="disabled")

        # 初次刷新
        self.refresh_stats()

    def refresh_stats(self):
        """简化统计：仅显示答题数、分类数、平均评分、总用时"""
        try:
            stats = self.trainer.get_overall_stats(
                user_id=self.current_user.get('id') if self.current_user else None
            )

            total_reviews = stats.get("total_reviews", 0)
            category_stats = stats.get("category_stats", {})
            avg_rating = float(stats.get("avg_rating", 0) or 0)
            total_seconds = float(stats.get("total_seconds_all", 0) or 0)

            # 文本拼接
            lines = []
            lines.append(f"总答题数：{total_reviews} 题")
            lines.append(f"平均评分：{avg_rating:.2f}")
            h = int(total_seconds) // 3600
            m = int(total_seconds) % 3600 // 60
            s = int(total_seconds) % 60
            # lines.append(f"总计用时：{int(total_seconds)} 秒")
            lines.append(f"总计用时：{h} 时 {m} 分 {s} 秒")
            lines.append("\n按分类统计：")
            for cat, data in category_stats.items():
                if isinstance(data, dict):
                    lines.append(f"  {cat}: {data.get('count', 0)} 题")
                else:
                    lines.append(f"  {cat}: {data} 题")

            # 更新文本框
            self.stats_text.configure(state="normal")
            self.stats_text.delete("1.0", "end")
            self.stats_text.insert("end", "\n".join(lines))
            self.stats_text.configure(state="disabled")

        except Exception as e:
            logger.exception("刷新统计失败")
            messagebox.showerror("统计失败", f"无法获取统计：{e}")

    def export_stats_json(self):
        try:
            stats = self.trainer.get_overall_stats(
                user_id=self.current_user.get('id') if self.current_user else None
            )
            path = filedialog.asksaveasfilename(defaultextension=".json", filetypes=[("JSON 文件", "*.json")])
            if not path:
                return
            with open(path, "w", encoding="utf-8") as f:
                json.dump(stats, f, ensure_ascii=False, indent=2, default=str)
            messagebox.showinfo("导出完成", f"统计已导出到：{path}")
        except Exception:
            logger.exception("导出统计失败")
            messagebox.showerror("导出失败", "导出统计失败，请查看日志")

    # --------------------
    # 题库 Tab（搜索/导入/新增）
    # --------------------
    def setup_question_bank_tab(self):
        """实现题库管理功能"""
        tab = self.tab_view.tab("题库")
        # 题目数量统计
        self.question_cnt_lbl = ctk.CTkLabel(tab, text="正在加载题目数量...", font=self.textbox_font)
        self.question_cnt_lbl.pack(anchor="w", padx=12, pady=(12, 6))
        top = ctk.CTkFrame(tab)
        top.pack(fill="x", padx=8, pady=8)
        # 搜索
        self.q_search_var = tk.StringVar()
        ctk.CTkEntry(top, placeholder_text="按关键词搜索题目", font=self.textbox_font,
                     textvariable=self.q_search_var).pack(side="left", padx=6, fill="x", expand=True)
        ctk.CTkButton(top, text="搜索", command=self.search_questions, font=self.textbox_font).pack(side="left", padx=6)
        ctk.CTkButton(top, text="导入 CSV", command=self.import_csv_from_ui, font=self.textbox_font).pack(side="left",
                                                                                                          padx=6)
        ctk.CTkButton(top, text="新增题目", command=self.add_question_dialog, font=self.textbox_font).pack(side="left",
                                                                                                           padx=6)

        # 题目列表
        self.q_listbox = tk.Listbox(tab, font=self.textbox_font)
        self.q_listbox.pack(fill="both", expand=True, padx=8, pady=8)
        self.q_listbox.bind("<<ListboxSelect>>", self.on_question_select)

        # 详情显示
        self.q_detail = ctk.CTkTextbox(tab, height=8, font=self.textbox_font)
        self.q_detail.pack(fill="x", padx=8, pady=(0, 8))
        self.refresh_question_list()

    def refresh_question_list(self):
        self.q_search_var.set("")
        self.search_questions()
        self.update_question_count()

    def search_questions(self):
        key = self.q_search_var.get().strip()
        try:
            cursor = self.trainer.db.conn.cursor(DictCursor)
            if key:
                sql = "SELECT id, question, category, difficulty, level FROM questions WHERE question LIKE %s LIMIT 200"
                cursor.execute(sql, (f"%{key}%",))
            else:
                sql = "SELECT id, question, category, difficulty, level FROM questions ORDER BY id DESC LIMIT 200"
                cursor.execute(sql)
            rows = cursor.fetchall()
            self.q_listbox.delete(0, "end")
            self.q_cache = rows
            for r in rows:
                label = f"#{r['id']} [{r.get('category') or '-'}] ({r.get('difficulty') or '-'}) L{r.get('level', 0)}: {r['question'][:80].replace('', '')}"
                self.q_listbox.insert("end", label)
        except Exception:
            logger.exception("题库搜索失败")
            messagebox.showerror("题库错误", "搜索题库失败，请查看日志")

    def update_question_count(self):
        """更新题目数量"""
        try:
            cursor = self.trainer.db.conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM questions")
            cnt = cursor.fetchone()[0]
            self.question_cnt_lbl.configure(text=f"当前共收录 {cnt} 道题")
        except Exception as e:
            logger.exception(f"题目数量获取失败：{e}")
            self.question_cnt_lbl.configure(text="题目数量获取失败")

    def on_question_select(self, event):
        sel = self.q_listbox.curselection()
        if not sel:
            return
        idx = sel[0]
        rec = self.q_cache[idx]
        txt = f"Q#{rec['id']}\n分类：{rec.get('category')}\n难度：{rec.get('difficulty')}\n掌握度：{rec.get('level')}\n\n题目：\n{rec.get('question')}"
        self.q_detail.configure(state="normal")
        self.q_detail.delete("1.0", "end")
        self.q_detail.insert("end", txt)
        self.q_detail.configure(state="disabled")

    def import_csv_from_ui(self):
        """通过文件对话框导入 CSV，调用 import_from_csv(file, mode='cli'|'web')"""
        path = filedialog.askopenfilename(title="选择 CSV 文件(.csv)", filetypes=[("CSV 文件", "*.csv")])
        if not path:
            return
        # 弹出确认
        if not messagebox.askyesno("确认导入", f"将导入文件：\n{path}\n导入过程中可能需要几秒钟，是否继续？"):
            return
        try:
            result = import_from_csv(path, mode="web")
            if 'error' in result:
                messagebox.showerror("导入失败", f"导入发生错误：{result['error']}")
            else:
                messagebox.showinfo("导入完成",
                                    f"导入完成：新增 {result.get('imported', 0)}，跳过 {result.get('skipped', 0)}，失败 {result.get('failed', 0)}")
                self.refresh_question_list()
        except Exception:
            logger.exception("CSV 导入失败")
            messagebox.showerror("导入失败", "CSV 导入失败，请查看日志")

    def add_question_dialog(self):
        """弹窗新增题目（同步写入 DB）"""
        dlg = ctk.CTkToplevel(self.app)
        dlg.title("新增题目")
        dlg.geometry("600x420")
        frm = ctk.CTkFrame(dlg, font=self.textbox_font)
        frm.pack(fill="both", expand=True, padx=12, pady=12)

        q_entry = ctk.CTkTextbox(frm, height=120, font=self.textbox_font)
        q_entry.pack(fill="x", pady=6)
        a_entry = ctk.CTkTextbox(frm, height=120, font=self.textbox_font)
        a_entry.pack(fill="x", pady=6)
        category_e = ctk.CTkEntry(frm, placeholder_text="分类（可选）", font=self.textbox_font)
        category_e.pack(fill="x", pady=6)
        diff_box = ctk.CTkComboBox(frm, values=["简单", "中等", "困难"], font=self.textbox_font)
        diff_box.set("中等")
        diff_box.pack(fill="x", pady=6)

        def do_add():
            qtxt = q_entry.get("1.0", "end").strip()
            atxt = a_entry.get("1.0", "end").strip()
            cat = category_e.get().strip()
            diff = diff_box.get()
            if not qtxt:
                messagebox.showwarning("输入错误", "题目不能为空")
                return
            try:
                self.trainer.add_question(qtxt, atxt, cat, diff)
                messagebox.showinfo("添加成功", "题目已添加")
                dlg.destroy()
                self.refresh_question_list()
            except Exception:
                logger.exception("新增题目失败")
                messagebox.showerror("失败", "新增题目失败，请查看日志")

        add_btn = ctk.CTkButton(frm, text="添加", command=do_add)
        add_btn.pack(pady=6)

    # --------------------
    # 个人中心 Tab（偏好/备份）
    # --------------------
    def setup_profile_tab(self):
        """实现个人设置功能"""
        tab = self.tab_view.tab("个人中心")
        frm = ctk.CTkFrame(tab)
        frm.pack(fill="both", expand=True, padx=12, pady=12)

        ctk.CTkLabel(frm, text="个人设置", font=self.textbox_font).pack(anchor="w", pady=(6, 8))
        # 主题选择
        ctk.CTkLabel(frm, text="主题：", font=self.textbox_font).pack(anchor="w")
        self.theme_var = tk.StringVar(value="Light")
        theme_combo = ctk.CTkComboBox(frm, values=["Light", "Dark", "System"], variable=self.theme_var,
                                      font=self.textbox_font)
        theme_combo.pack(anchor="w", pady=6)
        ctk.CTkButton(frm, text="应用主题", command=self.apply_theme, font=self.textbox_font).pack(pady=6, anchor="w")

        # 备份导出
        ctk.CTkButton(frm, text="导出题库备份（JSON）", command=self.backup_question_db, font=self.textbox_font).pack(
            pady=6, anchor="w")
        ctk.CTkButton(frm, text="清除本地 Session", command=self.clear_saved_session, font=self.textbox_font).pack(
            pady=6, anchor="w")

    def apply_theme(self):
        mode = self.theme_var.get()
        try:
            # customtkinter 接受 "light"/"dark"/"system" 小写或者首字母
            ctk.set_appearance_mode(mode.lower() if isinstance(mode, str) else mode)
            # 保存偏好
            if self.current_user:
                self.user_preferences['theme'] = mode
                self.save_user_preferences()
            messagebox.showinfo("已应用", f"主题已设置为：{mode}")
        except Exception:
            logger.exception("设置主题失败")
            messagebox.showerror("失败", "设置主题失败")

    def backup_question_db(self):
        """把 questions 表导出为 JSON（简易备份）"""
        path = filedialog.asksaveasfilename(defaultextension=".json", filetypes=[("JSON 文件", "*.json")])
        if not path:
            return
        try:

            cursor = self.trainer.db.conn.cursor(DictCursor)
            cursor.execute("SELECT * FROM questions")
            rows = cursor.fetchall()
            # rows 可能是 pymysql dict 类型，直接 json.dump 需转换
            with open(path, "w", encoding="utf-8") as f:
                json.dump(rows, f, ensure_ascii=False, default=str, indent=2)
            messagebox.showinfo("备份完成", f"题库已导出到：{path}")
        except Exception:
            logger.exception("备份失败")
            messagebox.showerror("备份失败", "备份失败，请查看日志")

    # --------------------
    # Session / Preferences / Persistence
    # --------------------
    def save_session_temp(self, username, password):
        """只保存用户名到 session.json（'记住我'）"""
        try:
            with open("data/session.json", "w", encoding="utf-8") as f:
                json.dump({"username": username,
                           "password": password,
                           "saved_at": datetime.now().isoformat()},
                          f, ensure_ascii=False)
        except Exception:
            logger.exception("保存 session 失败")

    def load_saved_session(self):
        try:
            if os.path.exists("data/session.json"):
                with open("data/session.json", "r", encoding="utf-8") as f:
                    data = json.load(f)
                username = data.get("username")
                password = data.get("password")
                if username and password:
                    # 自动尝试登录
                    user = self.trainer.db.verify_user(username, password)
                    if user:
                        self.current_user = user
                        self.show_main_interface()
                        self.load_user_preferences()
                        self.load_next_question()
                        logger.info(f"自动登录：{username}")
                        return
                # 如果失败，则仍然填充输入框
                self.username_entry.delete(0, "end")
                self.username_entry.insert(0, username or "")
                self.password_entry.delete(0, "end")
                self.password_entry.insert(0, password or "")
                self.remember_var.set(True)
        except Exception:
            logger.exception("加载 session 失败")

    def clear_saved_session(self):
        try:
            if os.path.exists("data/session.json"):
                os.remove("data/session.json")
            messagebox.showinfo("已清除", "本地 Session 已清除")
        except Exception:
            logger.exception("清除 session 失败")
            messagebox.showerror("失败", "清除失败")

    def load_user_preferences(self):
        """从本地文件加载用户偏好（prefs_{user_id}.json）"""
        if not self.current_user:
            return
        fname = f"prefs_{self.current_user['id']}.json"
        try:
            if os.path.exists(fname):
                with open(fname, "r", encoding="utf-8") as f:
                    self.user_preferences = json.load(f)
                # 应用主题偏好
                theme = self.user_preferences.get("theme")
                if theme:
                    try:
                        ctk.set_appearance_mode(theme.lower())
                    except Exception:
                        pass
        except Exception:
            logger.exception("加载用户偏好失败")

    def save_user_preferences(self):
        if not self.current_user:
            return
        fname = f"prefs_{self.current_user['id']}.json"
        try:
            with open(fname, "w", encoding="utf-8") as f:
                json.dump(self.user_preferences, f, ensure_ascii=False, indent=2)
        except Exception:
            logger.exception("保存用户偏好失败")

    # --------------------
    # 登出 / 退出
    # --------------------
    def logout(self):
        self.current_user = None
        # 停止计时
        self.stop_timer()
        # 隐藏主界面，显示登录界面
        try:
            if self.main_frame:
                self.main_frame.destroy()
                self.main_frame = None
        except Exception:
            pass
        self.auth_frame.pack(fill="both", expand=True)

    def on_closing(self):
        # 保存偏好
        try:
            if self.current_user:
                self.save_user_preferences()
        except Exception:
            logger.exception("退出时保存偏好失败")
        if messagebox.askokcancel("退出", "确认退出应用吗？"):
            try:
                # 停止计时
                self.stop_timer()
                if hasattr(self, 'trainer') and self.trainer:
                    self.trainer.close()
                    self._db_closed = True  # 设置标记避免重复
            except Exception as e:
                logger.exception(f"关闭数据库出错：{e}")
            finally:
                self.app.destroy()

    # --------------------
    # 运行
    # --------------------
    def run(self):
        """运行程序"""
        self.app.mainloop()

    def __del__(self):
        """清理资源 - 避免重复关闭数据库连接"""
        try:
            # 只有在数据库连接尚未关闭的情况下才关闭
            if hasattr(self, 'trainer') and self.trainer and not getattr(self, '_db_closed', False):
                self.trainer.close()
        except Exception as e:
            # 忽略"Already closed"错误
            if "Already closed" not in str(e):
                logger.error(f"析构函数中关闭数据库连接时出错: {str(e)}")


if __name__ == '__main__':
    app = InterviewTrainerGUI()
    app.run()
