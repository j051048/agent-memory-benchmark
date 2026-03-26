import json
import os

def generate_report():
    input_file = r'c:\Users\Fei\Desktop\AI应用\nexus-ai-command\test_memory_bench\benchmark_locomo_200_results.json'
    output_file = r'c:\Users\Fei\Desktop\AI应用\nexus-ai-command\test_memory_bench\benchmark_locomo_200_detailed_failures.md'
    
    if not os.path.exists(input_file):
        print(f"Error: {input_file} not found")
        return

    with open(input_file, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    results = data.get('results', [])
    # Filter correctly correctly based on bool
    failures = [r for r in results if not r.get('correct')]
    
    report = [
        "# LoCoMo 200题详细错题报告",
        "",
        "## 统计概览",
        "",
        f"- **总题目数**: 200",
        f"- **错误题目数**: {len(failures)}",
        f"- **准确率**: {((200-len(failures))/200 * 100):.1f}%",
        "",
        "---",
        "",
        "## 错题列表及详细分析",
        ""
    ]
    
    for i, fail in enumerate(failures):
        report.append(f"### {i+1}. 题目 ID: {fail['id']}")
        report.append("")
        report.append(f"- **场景用户**: {fail.get('user_id', 'N/A')}")
        report.append(f"- **问题**: {fail.get('query', 'N/A')}")
        report.append(f"- **预期准确答案**: {fail.get('gold_answers', [])}")
        report.append(f"- **模型实际回答**: {fail.get('answer', 'N/A')}")
        report.append(f"- **判定理由**: {fail.get('judge_reason', 'N/A')}")
        report.append(f"- **错误类别**: {fail.get('category', 'unknown')}")
        report.append("")
        
        # reasoning
        reasoning = fail.get('reasoning', '')
        if reasoning:
            report.append("**[模型推理轨迹]**")
            report.append("")
            report.append(f"> {reasoning}")
            report.append("")
        
        # Deep diagnosis
        report.append("**[深度诊断]**")
        report.append("")
        if "timeout" in reasoning.lower() or not fail.get('context', '').strip():
             report.append("- **核心瓶颈**: 检索层完全失效（超时或无匹配），导致模型根据极少量的噪声信息进行猜测。")
        elif fail.get('category') == "temporal":
             report.append("- **核心瓶颈**: 时间逻辑链条断裂。对话中频繁提到相对日期（'last Monday', 'yesterday'），由于召回片段可能缺乏明确的会话发起基准日期，模型计算出的绝对日期与标准答案产生了数日的偏差。")
        elif "contradict" in fail.get('judge_reason', '').lower() or "not align" in fail.get('judge_reason', '').lower():
             report.append("- **核心瓶颈**: 知识冲突解决能力弱。当多个相似对话片段共存时，模型无法区分哪一个是当前问题的真实上下文（例如不同周发生的同类活动）。")
        else:
             report.append("- **核心瓶颈**: 信息粒度不匹配。检索到了包含答案的大致段落，但关键实体（如具体地点、具体细节）被模型模糊化处理或概括掉了。")
        
        report.append("")
        report.append("---")
        report.append("")
        
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write("\n".join(report))
        
    print(f"Report successfully generated at: {output_file}")

if __name__ == "__main__":
    try:
        generate_report()
    except Exception as e:
        print(f"Error during report generation: {e}")
