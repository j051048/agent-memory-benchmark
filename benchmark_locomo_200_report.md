# Nexus AI LoCoMo 基准测试报告 (200 题)

## 总体概览

- **测试数据集**: LoCoMo (locomo10)
- **总测试题数**: 200
- **正确数量**: 173
- **准确率**: 86.50%
- **测试耗时**: 12.0 min

## 错误题目分析报告

共发现 27 个错误案例。以下为典型分析：

### 1. 错误分布 (按类别)

| 类别 | 错误数 | 占比 |
| :--- | :--- | :--- |
| temporal | 9 | 33.3% |
| multi-hop | 2 | 7.4% |
| single-hop | 9 | 33.3% |
| open-domain | 7 | 25.9% |

### 2. 典型错误示例

#### 错误案例 1 (ID: conv-26_q8)
- **问题**: When did Caroline give a speech at a school?
- **预期答案**: ['The week before 9 June 2023']
- **实际答案**: Caroline has not given a speech at a school.
- **判定理由**: The generated answer contradicts the gold answer instead of referencing the same time period.

#### 错误案例 2 (ID: conv-26_q9)
- **问题**: When did Caroline meet up with her friends, family, and mentors?
- **预期答案**: ['The week before 9 June 2023']
- **实际答案**: Caroline has met up with her support network on the occasion of a picnic that took place during the week of 29 June 2023.
- **判定理由**: The generated answer specifies a different date range (week of 29 June 2023) than the gold answer (week before 9 June 2023), making it misleading or inconsistent with the data provided.

#### 错误案例 3 (ID: conv-26_q10)
- **问题**: How long has Caroline had her current group of friends for?
- **预期答案**: ['4 years']
- **实际答案**: Caroline has had her current group of friends for around 10 years.
- **判定理由**: The generated answer provides a significantly different duration from the gold answer.

#### 错误案例 4 (ID: conv-26_q14)
- **问题**: Would Caroline still want to pursue counseling as a career if she hadn't received support growing up?
- **预期答案**: ['Likely no']
- **实际答案**: Yes, Caroline's motivation for pursuing counseling as a career is rooted in her own journey and experiences, emphasizing the importance of mental health and understanding.
- **判定理由**: The generated response does not align with the sentiment of the gold answer, which indicates 'Likely no.'

#### 错误案例 5 (ID: conv-26_q33)
- **问题**: When did Caroline go to a pride parade during the summer?
- **预期答案**: ['The week before 3 July 2023']
- **实际答案**: Caroline attended a pride parade on August 11, 2023.
- **判定理由**: The generated answer does not align with the date provided in the gold answer regarding Caroline's attendance at the pride parade.

#### 错误案例 6 (ID: conv-26_q34)
- **问题**: What events has Caroline participated in to help children?
- **预期答案**: ['Mentoring program, school speech']
- **实际答案**: Caroline has engaged in activities such as volunteering at LGBTQ youth centers and seeking counsel at adoption meetings to help children.
- **判定理由**: The generated answer diverges from the activities specified in the gold answer and mentions unrelated ones, making it not align with the question intent.

#### 错误案例 7 (ID: conv-26_q35)
- **问题**: When did Melanie go camping in July?
- **预期答案**: ['two weekends before 17 July 2023']
- **实际答案**: Melanie went camping in July during the week of June 20, 2023.
- **判定理由**: The generated answer does not align with the timeframe described in the gold answer.

#### 错误案例 8 (ID: conv-26_q36)
- **问题**: When did Caroline join a mentorship program?
- **预期答案**: ['The weekend before 17 July 2023']
- **实际答案**: Caroline joined a mentorship program for adoption support on 13 October 2023.
- **判定理由**: The generated answer provides a different timeframe than the gold answer, hence it cannot be considered correct.

#### 错误案例 9 (ID: conv-26_q52)
- **问题**: What are Melanie's pets' names?
- **预期答案**: ['Oliver, Luna, Bailey']
- **实际答案**: Melanie's pets' names are Oliver and Bailey.
- **判定理由**: The generated answer mentions two out of three names from the gold answer and omits 'Luna', hence it is considered incomplete and incorrect.

#### 错误案例 10 (ID: conv-26_q55)
- **问题**: What subject have Caroline and Melanie both painted?
- **预期答案**: ['Sunsets']
- **实际答案**: Caroline and Melanie have both painted scenes inspired by nature.
- **判定理由**: The generated answer does not explicitly mention sunsets, which is the specific topic referenced in the gold answer, hence it cannot be considered correct.

