"""
# -*- coding: utf-8 -*-
@File    : cli.py
@Author  : admin1
@Date    : 2025/8/18 14:26
@Description : 主程序
"""
import argparse
from datetime import datetime

from src.trainer import InterviewTrainer


def show_statistics(trainer):
    """显示统计信息"""
    stats = trainer.get_overall_stats()
    # 安全访问统计字段
    today_reviews = stats.get('today_reviews', 0)
    level_stats = stats.get('level_stats', {})
    category_stats = stats.get('category_stats', {})
    difficulty_stats = stats.get('difficulty_stats', {})
    print("\n=== 学习统计 ===")
    print(f"今日复习：{today_reviews} 题")
    # 掌握程度分布
    print("\n掌握程度分布：")
    for level in range(6):
        count = level_stats.get(level, 0)
        stars = '★' * level + '☆' * (5 - level)
        print(f"   {stars}({level}星)：{count}题")
    # 分类统计
    if stats['category_stats']:
        print("\n分类统计：")
        for category, count in category_stats.items():
            print(f"   {category}: {count}题")
    # 难度统计
    if stats['difficulty_stats']:
        print("\n难度统计：")
        for difficulty, count in difficulty_stats.items():
            print(f"   {difficulty}: {count}题")
    input("\n按回车键返回。。。")


def add_new_question(trainer):
    """添加新题目"""
    print("\n添加新题目：")
    question = input("请输入问题：").strip()
    if not question:
        print("问题不能为空")
        return
    answer = input("请输入参考答案(可选): ").strip()
    category = input("请输入分类(可选): ").strip()
    difficulty = input("请输入难度(简单/中等/困难，默认中等): ").strip()
    if difficulty not in ["简单", "中等", "困难"]:
        difficulty = "中等"
    trainer.add_question(question, answer, category, difficulty)
    print("√ 题目添加成功")


def initialize_database():
    """数据库初始化"""
    trainer = InterviewTrainer()
    trainer.initialize_database()
    trainer.close()
    print("数据库初始化完成")


def main():
    trainer = InterviewTrainer()
    print("\n=== 面试题自测训练器 ===")
    print("按回车开始答题 (输入 'q' 退出， 's' 查看统计，'a' 添加题目 )")
    session_start = datetime.now()
    while True:
        question_data = trainer.get_next_question()
        if not question_data:
            print("\n没有需要复习的题目！")
            break
        q_id = question_data['id']
        question = question_data['question']
        answer = question_data['answer'] or '暂无参考答案'
        category = question_data['category'] or "未分类"
        difficulty = question_data['difficulty'] or '中等'
        level = question_data['level']
        # 显示题目
        print(f"\n[{category}] [{difficulty}] (掌握程度：{level}/5)")
        print(f"问题：{question}")
        # 获取用户输入
        user_input = input("\n你的答案 (输入 's' 查看统计，'a' 添加题目，'q' 退出): ").strip()
        # 退出逻辑
        if user_input.lower() == 'q':
            break
        # 查看统计
        if user_input.lower() == 's':
            show_statistics(trainer)
            continue
        # 添加题目
        if user_input.lower() == 'a':
            add_new_question(trainer)
            continue
        # 显示答案
        print(f"\n参考答案：{answer}")
        # 获取用户自评价
        while True:
            try:
                rating = int(input("请评分(1-5分，5=完全掌握): "))
                if 1 <= rating <= 5:
                    break
                print("请输入1-5之间的数字")
            except ValueError:
                print("请输入有效数字")
        # 保存记录
        trainer.submit_answer(q_id, user_input, rating)
        print("记录已保存")
    # 展示本次总结
    session_end = datetime.now()
    duration = (session_end - session_start).seconds // 60
    summary = trainer.get_session_summary()
    stats = trainer.get_overall_stats()

    print(f"\n本次训练总结：")
    print(f"- 完成题目：{summary['question_reviewed']} 道")
    print(f"- 训练时长：{duration} 分钟")
    print(f"- 今日共复习：{stats['today_reviews']} 道题")
    trainer.close()


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="面试自测训练")
    parser.add_argument('--init', action='store_true', help="初始化数据库")
    args = parser.parse_args()
    if args.init:
        initialize_database()
    else:
        main()
