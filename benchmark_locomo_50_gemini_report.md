# Nexus AI LoCoMo 基准测试报告 (50 题 - Gemini)

## 总体概览

- **测试数据集**: LoCoMo (locomo10)
- **总测试题数**: 50
- **正确数量**: 30
- **准确率**: 60.00%
- **测试耗时**: 4.8 min

## 错误题目分析报告

共发现 20 个错误案例。以下为典型分析：

### 1. 错误分布 (按类别)

| 类别 | 错误数 | 占比 |
| :--- | :--- | :--- |
| single-hop | 5 | 25.0% |
| temporal | 13 | 65.0% |
| multi-hop | 2 | 10.0% |

### 2. 典型错误示例

#### 错误案例 1 (ID: conv-26_q3)
- **问题**: What did Caroline research?
- **预期答案**: ['Adoption agencies']
- **实际答案**: On 2023-05-08, Caroline mentioned she was going to do research regarding continuing her education and exploring career options, specifically in the fields of counseling or mental health.
- **判定理由**: The generated answer discusses career and education research, whereas the gold answer specifically mentions adoption agencies.

#### 错误案例 2 (ID: conv-26_q5)
- **问题**: When did Melanie run a charity race?
- **预期答案**: ['The sunday before 25 May 2023']
- **实际答案**: The context lacks information regarding when or if Melanie ran a charity race.
- **判定理由**: The gold answer provides a specific date, indicating the information was available in the context, but the generated answer incorrectly claimed it was missing.

#### 错误案例 3 (ID: conv-26_q6)
- **问题**: When is Melanie planning on going camping?
- **预期答案**: ['June 2023']
- **实际答案**: The context does not provide a specific date for a future camping trip Melanie is planning. However, it notes she went camping with her family around 2023-07-08 to 2023-07-09, and another trip was mentioned as having occurred a few weeks prior to September 13, 2023.
- **判定理由**: The generated answer incorrectly states that the context does not provide a date, whereas the gold answer specifies June 2023.

#### 错误案例 4 (ID: conv-26_q7)
- **问题**: What is Caroline's relationship status?
- **预期答案**: ['Single']
- **实际答案**: The provided context does not contain information about Caroline's relationship status.
- **判定理由**: The generated answer incorrectly claims the information is missing, whereas the gold answer provides a specific status.

#### 错误案例 5 (ID: conv-26_q8)
- **问题**: When did Caroline give a speech at a school?
- **预期答案**: ['The week before 9 June 2023']
- **实际答案**: The provided context does not contain information about Caroline giving a speech at a school.
- **判定理由**: The generated answer incorrectly claims the information is missing, whereas the gold answer provides a specific date, indicating the information was available.

#### 错误案例 6 (ID: conv-26_q9)
- **问题**: When did Caroline meet up with her friends, family, and mentors?
- **预期答案**: ['The week before 9 June 2023']
- **实际答案**: 2023-09-09
- **判定理由**: The generated answer provides a date in September 2023, whereas the gold answer refers to a week in early June 2023.

#### 错误案例 7 (ID: conv-26_q10)
- **问题**: How long has Caroline had her current group of friends for?
- **预期答案**: ['4 years']
- **实际答案**: The context does not provide information regarding exactly how long Caroline has had her current group of friends, although it notes that she attended a Pride festival with them 'last year' (2022).
- **判定理由**: The generated answer incorrectly states that the information is not provided, whereas the gold answer specifies a duration of 4 years.

#### 错误案例 8 (ID: conv-26_q12)
- **问题**: How long ago was Caroline's 18th birthday?
- **预期答案**: ['10 years ago']
- **实际答案**: The context lacks the information to determine when Caroline's 18th birthday was.
- **判定理由**: The gold answer provides a specific time frame, indicating the information was available, but the generated answer claims it is missing.

#### 错误案例 9 (ID: conv-26_q14)
- **问题**: Would Caroline still want to pursue counseling as a career if she hadn't received support growing up?
- **预期答案**: ['Likely no']
- **实际答案**: The context does not provide enough information to determine if Caroline would still pursue counseling if she hadn't received support growing up; it only details that her current interest in the field is motivated by her recent experiences with LGBTQ support groups and her desire to help others with similar life stories.
- **判定理由**: The generated answer claims the information is not available, while the gold answer indicates a clear answer can be derived from the context.

#### 错误案例 10 (ID: conv-26_q20)
- **问题**: When did Melanie go to the museum?
- **预期答案**: ['5 July 2023']
- **实际答案**: The provided context does not contain information about Melanie going to a museum.
- **判定理由**: The gold answer provides a specific date, indicating the information was available, but the generated answer failed to find it.

