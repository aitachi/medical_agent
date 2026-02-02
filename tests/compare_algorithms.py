# -*- coding: utf-8 -*-
"""
多算法对比测试 - MLP vs SVM vs GBoost vs 逻辑回归
使用相同的训练/测试划分进行公平对比
"""

import asyncio
import sys
import os
import json
import numpy as np
from datetime import datetime
from collections import defaultdict

# sklearn imports
from sklearn.model_selection import train_test_split
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.preprocessing import LabelEncoder
from sklearn.linear_model import LogisticRegression
from sklearn.svm import LinearSVC, SVC
from sklearn.neural_network import MLPClassifier
from sklearn.ensemble import GradientBoostingClassifier
import joblib

# 添加项目路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


class MultiAlgorithmComparator:
    """多算法对比测试器"""

    def __init__(self, data_path: str = None):
        if data_path is None:
            data_path = os.path.join(
                os.path.dirname(__file__),
                "algorithem",
                "test_dataset_5000.json"
            )
        self.data_path = data_path
        self.results = {
            "timestamp": datetime.now().isoformat(),
            "algorithms": {}
        }

    def load_data(self):
        """加载数据"""
        print("=" * 70)
        print("多算法对比测试")
        print("=" * 70)
        print(f"\n加载数据: {self.data_path}")

        with open(self.data_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
            samples = data['samples']

        texts = [s['text'] for s in samples]
        labels = [s['intent'] for s in samples]

        print(f"总样本数: {len(texts)}")

        # 80/20 划分（与之前实验一致）
        X_train, X_test, y_train, y_test = train_test_split(
            texts, labels,
            test_size=0.2,
            random_state=42,
            stratify=labels
        )

        print(f"训练集: {len(X_train)}")
        print(f"测试集: {len(X_test)}")

        return X_train, X_test, y_train, y_test

    def create_vectorizer(self, texts):
        """创建TF-IDF向量化器"""
        return TfidfVectorizer(
            analyzer='char',
            ngram_range=(1, 3),
            min_df=2,
            max_df=0.95,
            max_features=3366
        )

    def train_and_evaluate(self, name, model, X_train, X_test, y_train, y_test, vectorizer):
        """训练并评估模型"""
        print(f"\n{'-'*70}")
        print(f"算法: {name}")
        print(f"{'-'*70}")

        import time
        start_time = time.time()

        # 训练
        model.fit(X_train, y_train)
        train_time = time.time() - start_time

        # 预测
        train_pred = model.predict(X_train)
        test_pred = model.predict(X_test)

        # 计算准确率
        train_acc = np.mean(train_pred == y_train)
        test_acc = np.mean(test_pred == y_test)

        # 计算泛化差距
        gen_gap = train_acc - test_acc

        # 按意图统计
        intent_stats = defaultdict(lambda: {"total": 0, "correct": 0})
        for pred, true in zip(test_pred, y_test):
            intent_stats[true]["total"] += 1
            if pred == true:
                intent_stats[true]["correct"] += 1

        print(f"训练准确率: {train_acc*100:.2f}%")
        print(f"测试准确率: {test_acc*100:.2f}%")
        print(f"泛化差距: {gen_gap*100:.2f}%")
        print(f"训练时间: {train_time:.2f}秒")

        # 打印各意图准确率
        print(f"\n各意图测试准确率:")
        for intent, stats in sorted(intent_stats.items()):
            acc = stats["correct"] / stats["total"] * 100
            print(f"  {intent}: {acc:.2f}% ({stats['correct']}/{stats['total']})")

        return {
            "train_accuracy": train_acc,
            "test_accuracy": test_acc,
            "generalization_gap": gen_gap,
            "train_time": train_time,
            "by_intent": dict(intent_stats)
        }

    def test_logistic_regression(self, X_train, X_test, y_train, y_test, vectorizer):
        """逻辑回归"""
        model = LogisticRegression(
            C=1.0,
            max_iter=1000,
            random_state=42
        )
        return self.train_and_evaluate("逻辑回归 (Logistic Regression)", model, X_train, X_test, y_train, y_test, vectorizer)

    def test_linear_svm(self, X_train, X_test, y_train, y_test, vectorizer):
        """线性SVM"""
        model = LinearSVC(
            C=1.0,
            max_iter=1000,
            random_state=42
        )
        return self.train_and_evaluate("线性SVM (Linear SVM)", model, X_train, X_test, y_train, y_test, vectorizer)

    def test_rbf_svm(self, X_train, X_test, y_train, y_test, vectorizer):
        """RBF SVM"""
        model = SVC(
            C=1.0,
            kernel='rbf',
            gamma='scale',
            random_state=42
        )
        return self.train_and_evaluate("RBF SVM (RBF Kernel)", model, X_train, X_test, y_train, y_test, vectorizer)

    def test_mlp(self, X_train, X_test, y_train, y_test, vectorizer):
        """MLP神经网络"""
        model = MLPClassifier(
            hidden_layer_sizes=(128, 64),
            activation='relu',
            solver='adam',
            alpha=0.0001,
            batch_size=32,
            learning_rate_init=0.001,
            max_iter=500,
            early_stopping=False,  # 关闭early_stopping避免稀疏矩阵问题
            random_state=42
        )
        return self.train_and_evaluate("MLP神经网络", model, X_train, X_test, y_train, y_test, vectorizer)

    def test_gboost(self, X_train, X_test, y_train, y_test, vectorizer):
        """梯度提升"""
        model = GradientBoostingClassifier(
            n_estimators=100,
            learning_rate=0.1,
            max_depth=3,
            random_state=42
        )
        return self.train_and_evaluate("梯度提升 (GBoost)", model, X_train, X_test, y_train, y_test, vectorizer)

    def print_comparison_table(self):
        """打印对比表格"""
        print("\n" + "=" * 70)
        print("算法对比结果汇总")
        print("=" * 70)

        algorithms = self.results["algorithms"]

        print(f"\n{'算法':<25} {'训练准确率':<12} {'测试准确率':<12} {'泛化差距':<12} {'训练时间':<10}")
        print("-" * 70)

        # 按测试准确率排序
        sorted_alg = sorted(algorithms.items(), key=lambda x: -x[1]["test_accuracy"])

        for name, result in sorted_alg:
            print(f"{name:<25} {result['train_accuracy']*100:>10.2f}%  {result['test_accuracy']*100:>10.2f}%  "
                  f"{result['generalization_gap']*100:>+9.2f}%  {result['train_time']:>8.2f}s")

        # 找出最佳
        best = sorted_alg[0]
        print(f"\n最佳算法: {best[0]} - 测试准确率 {best[1]['test_accuracy']*100:.2f}%")

    def save_report(self):
        """保存报告"""
        report_dir = os.path.join(os.path.dirname(__file__), "algorithem")
        os.makedirs(report_dir, exist_ok=True)

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        report_path = os.path.join(report_dir, f"algorithm_comparison_{timestamp}.json")

        with open(report_path, 'w', encoding='utf-8') as f:
            json.dump(self.results, f, ensure_ascii=False, indent=2)

        print(f"\n报告已保存: {report_path}")
        return report_path

    def run(self):
        """运行对比测试"""
        # 加载数据
        X_train_raw, X_test_raw, y_train, y_test = self.load_data()

        # 创建向量化器并转换数据
        print(f"\n创建TF-IDF特征 (字符级 1-3gram)...")
        vectorizer = self.create_vectorizer(X_train_raw)
        X_train = vectorizer.fit_transform(X_train_raw)
        X_test = vectorizer.transform(X_test_raw)
        print(f"特征维度: {X_train.shape[1]}")

        # 测试各个算法
        print("\n" + "=" * 70)
        print("开始算法对比测试...")
        print("=" * 70)

        self.results["algorithms"]["logistic_regression"] = \
            self.test_logistic_regression(X_train, X_test, y_train, y_test, vectorizer)

        self.results["algorithms"]["linear_svm"] = \
            self.test_linear_svm(X_train, X_test, y_train, y_test, vectorizer)

        self.results["algorithms"]["rbf_svm"] = \
            self.test_rbf_svm(X_train, X_test, y_train, y_test, vectorizer)

        self.results["algorithms"]["mlp"] = \
            self.test_mlp(X_train, X_test, y_train, y_test, vectorizer)

        self.results["algorithms"]["gboost"] = \
            self.test_gboost(X_train, X_test, y_train, y_test, vectorizer)

        # 打印对比
        self.print_comparison_table()
        self.save_report()


def main():
    """主函数"""
    comparator = MultiAlgorithmComparator()
    comparator.run()

    print("\n" + "=" * 70)
    print("测试完成!")
    print("=" * 70)


if __name__ == "__main__":
    main()
