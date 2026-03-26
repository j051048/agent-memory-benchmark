import json
import os

def generate_report(json_path, output_path):
    with open(json_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    summary = data['summary']
    results = data['results']
    
    report = []
    report.append("# Nexus-AI-Command 记忆基准测试报告 (v20)")
    report.append(f"\n## 总体概览")
    report.append(f"- **总测试题数**: {summary['total']}")
    report.append(f"- **正确数量**: {summary['correct']}")
    report.append(f"- **准确率**: {summary['accuracy'] * 100:.2f}%")
    report.append(f"- **索引构建耗时**: {summary['ingest_time_s']:.2f}s")
    
    report.append("\n## 详细结果列表")
    report.append("| ID | 结果 | 预期答案 | 代理答案 | 判定分 |")
    report.append("| --- | --- | --- | --- | --- |")
    
    incorrect_examples = []
    correct_examples = []
    
    for res in results:
        status = "✅" if res['correct'] else "❌"
        # Since PersonaMem gold_answers is usually a list with one item
        gold = res['gold_answers'][0] if isinstance(res['gold_answers'], list) and len(res['gold_answers']) > 0 else res['gold_answers']
        score = 1.0 if res['correct'] else 0.0
        report.append(f"| {str(res['id'])[:8]}... | {status} | {gold} | {res['answer']} | {score} |")
        
        if not res['correct'] and len(incorrect_examples) < 3:
            incorrect_examples.append(res)
        if res['correct'] and len(correct_examples) < 2:
            correct_examples.append(res)

    report.append("\n## 错误案例分析")
    for i, ex in enumerate(incorrect_examples):
        gold = ex['gold_answers'][0] if isinstance(ex['gold_answers'], list) and len(ex['gold_answers']) > 0 else ex['gold_answers']
        report.append(f"\n### 错误案例 {i+1}")
        report.append(f"**问题**: \n```text\n{ex['query']}\n```")
        report.append(f"**预期正确选项**: {gold}")
        report.append(f"**代理回复**: {ex['answer']}")
        report.append(f"**代理推理**: {ex['reasoning']}")
        report.append(f"**参考上下文**: \n```text\n{ex['context'][:800]}...\n```")

    report.append("\n## 正确案例参考")
    for i, ex in enumerate(correct_examples):
        report.append(f"\n### 正确案例 {i+1}")
        report.append(f"**问题**: \n```text\n{ex['query']}\n```")
        report.append(f"**代理回复**: {ex['answer']}")
        report.append(f"**代理推理**: {ex['reasoning']}")

    with open(output_path, 'w', encoding='utf-8') as f:
        f.write('\n'.join(report))

if __name__ == "__main__":
    json_path = r'c:\Users\Fei\Desktop\AI应用\nexus-ai-command\test_memory_bench\benchmark_results_v20.json'
    output_path = r'c:\Users\Fei\Desktop\AI应用\nexus-ai-command\test_memory_bench\benchmark_report_v20.md'
    generate_report(json_path, output_path)
