import json
import os

def analyze():
    input_path = r'c:\Users\Fei\Desktop\AI应用\nexus-ai-command\test_memory_bench\benchmark_locomo_100_results.json'
    output_path = r'c:\Users\Fei\Desktop\AI应用\nexus-ai-command\test_memory_bench\locomo_failures_summary.json'
    
    if not os.path.exists(input_path):
        print(f"File not found: {input_path}")
        return

    with open(input_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    failures = [r for r in data['results'] if not r.get('correct', False)]
    
    summary = {
        "summary": data['summary'],
        "total_failures": len(failures),
        "by_category": {}
    }
    
    for f in failures:
        cat = f.get('category', 'unknown')
        if cat not in summary['by_category']:
            summary['by_category'][cat] = []
        summary['by_category'][cat].append({
            "id": f['id'],
            "query": f['query'],
            "answer": f['answer'],
            "gold": f['gold_answers'],
            "reason": f.get('judge_reason', f.get('reasoning', ''))
        })
        
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(summary, f, indent=2, ensure_ascii=False)
    print(f"Summary saved to {output_path}")

if __name__ == "__main__":
    analyze()
