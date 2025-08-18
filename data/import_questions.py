"""
# -*- coding: utf-8 -*-
@File    : import_questions.py
@Author  : admin1
@Date    : 2025/8/18 14:10
@Description : 题目导入
"""
import csv

from src.trainer import InterviewTrainer


def import_from_csv(file_path):
    """从csv文件导入题目"""
    trainer = InterviewTrainer()
    imported_cnt = 0
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                if 'question' not in row:
                    print(f"跳过无效行：{row}")
                    continue
                # 导入题目
                question = row['question']
                answer = row.get('answer', '')
                category = row.get('category', '')
                difficulty = row.get('difficulty', '中等')
                trainer.add_question(question, answer, category, difficulty)
                # print(f"读取的题目信息：{question}")
                # print(f"读取的题目信息：{answer}")
                # print(f"读取的题目信息：{category}")
                # print(f"读取的题目信息：{difficulty}")
                imported_cnt += 1
        print(f"成功导入 {imported_cnt} 道题目")
    except Exception as e:
        print(f"导入失败：{str(e)}")
    finally:
        trainer.close()


if __name__ == '__main__':
    # import sys
    #
    # if len(sys.argv) != 2:
    #     print(f"用法：python import_question.py <csv文件路径>")
    #     sys.exit()
    # csv_file = sys.argv[1]
    # import_from_csv(csv_file)
    path = r"E:\FileMgr\questions.csv"
    import_from_csv(path)