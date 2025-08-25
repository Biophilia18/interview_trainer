"""
# -*- coding: utf-8 -*-
@File    : main_gui.py
@Author  : admin1
@Date    : 2025/8/25 16:48
@Description : GUI实现
"""
# main_gui.py
import threading
import time
import tkinter as tk
from tkinter import messagebox
import customtkinter as ctk

# 假设你的项目里可以这样导入
from src.trainer import InterviewTrainer

ctk.set_appearance_mode("System")  # "Dark" / "Light"
ctk.set_default_color_theme("blue")


class TrainerApp(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("Interview Trainer - 桌面版")
        self.geometry("900x600")

        # session
        self.user = None  # {'id':..., 'username':...}
        self.trainer = None

        # UI 布局：左侧导航，右侧内容区
        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure((1,), weight=1)

        self.sidebar = ctk.CTkFrame(self, width=220)
        self.sidebar.grid(row=0, column=0, sticky="nsew", padx=12, pady=12)
        self.main_frame = ctk.CTkFrame(self)
        self.main_frame.grid(row=0, column=1, sticky="nsew", padx=12, pady=12)

        # Sidebar contents
        self.logo = ctk.CTkLabel(self.sidebar, text="Interview Trainer", font=ctk.CTkFont(size=18, weight="bold"))
        self.logo.pack(pady=(12, 20))

        self.btn_login = ctk.CTkButton(self.sidebar, text="登录 / 注册", command=self.show_login)
        self.btn_login.pack(fill="x", padx=12, pady=(0, 8))

        self.btn_take = ctk.CTkButton(self.sidebar, text="开始答题", command=self.show_question, state="disabled")
        self.btn_take.pack(fill="x", padx=12, pady=8)

        self.btn_stats = ctk.CTkButton(self.sidebar, text="学习统计", command=self.show_stats, state="disabled")
        self.btn_stats.pack(fill="x", padx=12, pady=8)

        self.btn_logout = ctk.CTkButton(self.sidebar, text="登出", fg_color="tomato", command=self.logout, state="disabled")
        self.btn_logout.pack(fill="x", padx=12, pady=8)

        # content placeholders
        self.current_widget = None

        # show login at start
        self.show_login()

    # -------------------------
    # Session actions
    # -------------------------
    def ensure_trainer(self):
        if not self.trainer:
            self.trainer = InterviewTrainer()

    def login_success(self, user):
        self.user = user
        self.btn_take.configure(state="normal")
        self.btn_stats.configure(state="normal")
        self.btn_logout.configure(state="normal")
        self.btn_login.configure(text=f"用户：{user['username']}", state="disabled")
        messagebox.showinfo("登录成功", f"欢迎，{user['username']}")

    def logout(self):
        if self.trainer:
            try:
                self.trainer.close()
            except Exception:
                pass
        self.trainer = None
        self.user = None
        self.btn_take.configure(state="disabled")
        self.btn_stats.configure(state="disabled")
        self.btn_logout.configure(state="disabled")
        self.btn_login.configure(text="登录 / 注册", state="normal")
        self.show_login()
        messagebox.showinfo("已登出", "您已退出登录")

    # -------------------------
    # Views
    # -------------------------
    def clear_main(self):
        for w in self.main_frame.winfo_children():
            w.destroy()

    def show_login(self):
        self.clear_main()
        lf = ctk.CTkFrame(self.main_frame)
        lf.pack(fill="both", expand=True, padx=12, pady=12)

        title = ctk.CTkLabel(lf, text="登录或注册", font=ctk.CTkFont(size=20, weight="bold"))
        title.pack(pady=(8, 18))

        uname = ctk.CTkEntry(lf, placeholder_text="用户名")
        uname.pack(pady=8, fill="x")
        pwd = ctk.CTkEntry(lf, placeholder_text="密码", show="*")
        pwd.pack(pady=8, fill="x")

        # 切换到注册表单
        def do_register():
            u = uname.get().strip()
            p = pwd.get().strip()
            if not u or not p:
                messagebox.showwarning("输入错误", "用户名/密码不能为空")
                return
            # 在子线程执行 DB 操作以防卡 UI
            def reg_task():
                self.ensure_trainer()
                created = self.trainer.db.create_user(u, p)
                if created:
                    self.after(0, lambda: messagebox.showinfo("注册成功", "注册成功，请登录"))
                else:
                    self.after(0, lambda: messagebox.showerror("注册失败", "用户名已存在或创建失败"))
            threading.Thread(target=reg_task, daemon=True).start()

        def do_login():
            u = uname.get().strip()
            p = pwd.get().strip()
            if not u or not p:
                messagebox.showwarning("输入错误", "用户名/密码不能为空")
                return

            def login_task():
                self.ensure_trainer()
                user = self.trainer.db.verify_user(u, p)
                if user:
                    # set session in main thread
                    self.after(0, lambda: self.login_success(user))
                    self.after(0, lambda: self.show_question())
                else:
                    self.after(0, lambda: messagebox.showerror("登录失败", "用户名或密码错误"))
            threading.Thread(target=login_task, daemon=True).start()

        btn_login = ctk.CTkButton(lf, text="登录", command=do_login)
        btn_login.pack(pady=(12, 6), fill="x")
        btn_register = ctk.CTkButton(lf, text="注册", command=do_register, fg_color="#2b8f2b")
        btn_register.pack(pady=(6, 6), fill="x")

    def show_question(self):
        if not self.user:
            messagebox.showwarning("未登录", "请先登录")
            return
        self.clear_main()
        frame = ctk.CTkFrame(self.main_frame)
        frame.pack(fill="both", expand=True, padx=12, pady=12)

        # question card area
        card = ctk.CTkFrame(frame)
        card.pack(fill="both", expand=True, padx=8, pady=8)

        # placeholders for UI elements we will update
        lbl_meta = ctk.CTkLabel(card, text="", anchor="w")
        lbl_meta.pack(fill="x", pady=(8, 2), padx=6)
        txt_question = ctk.CTkTextbox(card, height=160, wrap="word")
        txt_question.pack(fill="both", expand=False, padx=6, pady=6)
        answer_box = ctk.CTkTextbox(card, height=140, wrap="word")
        answer_box.pack(fill="both", expand=False, padx=6, pady=6)

        # rating and buttons
        controls = ctk.CTkFrame(card)
        controls.pack(fill="x", padx=6, pady=6)
        rating_var = tk.IntVar(value=3)
        rating_menu = ctk.CTkOptionMenu(controls, values=["1","2","3","4","5"], command=lambda v: rating_var.set(int(v)))
        rating_menu.set("3")
        rating_menu.pack(side="left", padx=(0,12))

        btn_show_answer = ctk.CTkButton(controls, text="查看参考答案")
        btn_show_answer.pack(side="left", padx=6)
        btn_submit = ctk.CTkButton(controls, text="提交")
        btn_submit.pack(side="right", padx=6)
        btn_next = ctk.CTkButton(controls, text="下一题", command=lambda: load_question())
        btn_next.pack(side="right", padx=(6,0))

        # timing
        timer_label = ctk.CTkLabel(card, text="已用时：0s")
        timer_label.pack(anchor="e", padx=8, pady=(0,8))

        # internal state
        state = {
            "q": None,
            "start_ts": None,
            "timer_running": False,
            "timer_job": None
        }

        def update_timer_display():
            if not state["timer_running"]:
                return
            elapsed = int(time.time() - state["start_ts"])
            timer_label.configure(text=f"已用时：{elapsed}s")
            state["timer_job"] = self.after(500, update_timer_display)

        def start_timer():
            state["start_ts"] = time.time()
            state["timer_running"] = True
            update_timer_display()

        def stop_timer():
            state["timer_running"] = False
            if state["timer_job"]:
                self.after_cancel(state["timer_job"])
                state["timer_job"] = None

        def load_question():
            # 从后端拿题（在线程中）
            txt_question.delete("0.0", "end")
            answer_box.delete("0.0", "end")
            lbl_meta.configure(text="加载中...")
            stop_timer()

            def task():
                self.ensure_trainer()
                q = self.trainer.get_next_question()
                if not q:
                    self.after(0, lambda: messagebox.showinfo("完成", "没有更多题了"))
                    return
                state["q"] = q
                self.after(0, lambda: populate_question(q))
            threading.Thread(target=task, daemon=True).start()

        def populate_question(q):
            meta = f"分类：{q.get('category') or '未分类'}    难度：{q.get('difficulty') or '中等'}    掌握：{q.get('level') or 0}/5"
            lbl_meta.configure(text=meta)
            txt_question.delete("0.0", "end")
            txt_question.insert("0.0", q.get("question") or "")
            answer_box.delete("0.0", "end")
            # 放置 placeholder 提示用户在此写答案
            answer_box.insert("0.0", "")
            rating_menu.set(str(q.get('level') or 3))
            # start timer when question displayed
            start_timer()

        def toggle_answer():
            q = state["q"]
            if not q:
                messagebox.showwarning("提示", "当前没有题目")
                return
            # 弹窗显示参考答案
            messagebox.showinfo("参考答案", q.get("answer") or "未提供参考答案")

        def do_submit():
            q = state["q"]
            if not q:
                messagebox.showwarning("提示", "当前没有题目")
                return
            user_ans = answer_box.get("0.0", "end").strip()
            rating = int(rating_var.get() or 3)
            elapsed = int(time.time() - state["start_ts"]) if state["start_ts"] else None

            # run DB save in thread
            def submit_task():
                self.ensure_trainer()
                rec_id = self.trainer.submit_answer(q['id'], user_ans, rating, user_id=self.user['id'], duration_seconds=elapsed)
                if rec_id:
                    self.after(0, lambda: messagebox.showinfo("提交成功", "已保存本次记录"))
                    # optionally open review window
                    self.after(0, lambda: self.show_review(rec_id))
                else:
                    self.after(0, lambda: messagebox.showerror("提交失败", "保存记录失败"))
            threading.Thread(target=submit_task, daemon=True).start()
            stop_timer()

        btn_show_answer.configure(command=toggle_answer)
        btn_submit.configure(command=do_submit)

        # initial load
        load_question()

    def show_review(self, record_id):
        # 获取并展示 review 内容
        def task():
            self.ensure_trainer()
            db = self.trainer.db
            cursor = db.conn.cursor()
            cursor.execute('''
                SELECT r.id as record_id, r.user_answer, r.rating, r.duration_seconds, r.reviewed_at,
                       q.id as question_id, q.question, q.answer, q.category, q.difficulty
                FROM review_records r
                JOIN questions q ON r.question_id = q.id
                WHERE r.id = %s
            ''', (record_id,))
            row = cursor.fetchone()
            if not row:
                self.after(0, lambda: messagebox.showerror("错误", "记录未找到"))
                return
            # convert row (tuple) into readable string: we'll show a simple popup
            # If you use DictCursor change how you fetch - adapt as needed
            # For safety, just format generic
            text = f"题目:\n{row[6]}\n\n参考答案:\n{row[7]}\n\n你的答案:\n{row[1]}\n\n评分: {row[2]}\n用时: {row[3]}s\n时间: {row[4]}"
            self.after(0, lambda: messagebox.showinfo("回顾", text))
        threading.Thread(target=task, daemon=True).start()

    def show_stats(self):
        if not self.user:
            messagebox.showwarning("未登录", "请先登录")
            return
        self.clear_main()
        frame = ctk.CTkFrame(self.main_frame)
        frame.pack(fill="both", expand=True, padx=12, pady=12)

        title = ctk.CTkLabel(frame, text="学习统计", font=ctk.CTkFont(size=20, weight="bold"))
        title.pack(pady=(8, 12))

        # container for stats
        stats_text = tk.Text(frame, height=20, wrap="word")
        stats_text.pack(fill="both", expand=True, padx=6, pady=6)

        def load_stats():
            self.ensure_trainer()
            stats = self.trainer.get_overall_stats(user_id=self.user['id'])
            # pretty print stats into text widget
            out = []
            out.append(f"今日复习：{stats.get('today_reviews',0)} 题")
            if 'total_seconds_today' in stats:
                out.append(f"今日总用时：{stats.get('total_seconds_today',0)} 秒")
            if 'avg_seconds_all' in stats:
                out.append(f"历史平均用时：{round(stats.get('avg_seconds_all',0),1)} 秒")
            out.append("\n掌握程度：")
            for k,v in (stats.get('level_stats') or {}).items():
                out.append(f"  等级 {k}: {v} 题")
            out.append("\n按分类：")
            cs = stats.get('category_stats') or {}
            if cs:
                for cat, data in cs.items():
                    if isinstance(data, dict):
                        out.append(f"  {cat}: 题数 {data.get('count')}, 总用时 {data.get('total_seconds')}s, 平均 {round(data.get('avg_seconds',0),1)}s")
                    else:
                        out.append(f"  {cat}: 题数 {data}")
            else:
                out.append("  无")
            out.append("\n按难度：")
            ds = stats.get('difficulty_stats') or {}
            if ds:
                for diff, data in ds.items():
                    if isinstance(data, dict):
                        out.append(f"  {diff}: 题数 {data.get('count')}, 总用时 {data.get('total_seconds')}s, 平均 {round(data.get('avg_seconds',0),1)}s")
                    else:
                        out.append(f"  {diff}: 题数 {data}")
            else:
                out.append("  无")
            stats_text.delete("1.0", "end")
            stats_text.insert("1.0", "\n".join(out))

        # load in background
        threading.Thread(target=load_stats, daemon=True).start()

        btn_refresh = ctk.CTkButton(frame, text="刷新", command=lambda: threading.Thread(target=load_stats, daemon=True).start())
        btn_refresh.pack(pady=8)

# Run app
if __name__ == "__main__":
    app = TrainerApp()
    app.mainloop()

