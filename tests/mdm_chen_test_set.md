# Mdm Chen 测试集

**用户档案**：陈女士（Mdm Chen），68岁，女，T2D，Metformin 500mg，独居，女儿在澳洲，英语用户。

---

## 模块一：食物咨询（RAG 本地知识）

| ID | 输入 | 预期 Intent | 预期 Sub-intent | 测试亮点 |
|----|------|------------|----------------|---------|
| F1 | Is char kway teow ok for me to eat? | medical | food_inquiry | RAG 新加坡食物 GI 知识 |
| F2 | Can I eat nasi lemak for breakfast? | medical | food_inquiry | RAG 椰浆饭，桑巴酱高GI提示 |
| F3 | What about roti prata, is it high GI? | medical | food_inquiry | RAG 本地食物 |
| F4 | I had wonton noodles for dinner tonight, will my blood sugar spike? | medical | food_inquiry | 结合 food_log 云吞面记录 |
| F5 | Is brown rice better than white rice for diabetes? | medical | food_inquiry | RAG 基础营养知识 |

---

## 模块二：血糖数据（CGM 集成）

| ID | 输入 | 预期 Intent | 预期 Sub-intent | 测试亮点 |
|----|------|------------|----------------|---------|
| G1 | My glucose reading is 9.5 after lunch, is that normal? | medical | glucose_query | 结合近期 CGM 数据 |
| G2 | What has my blood sugar been like this week? | medical | glucose_query | weekly glucose summary |
| G3 | Why does my sugar always go high after dinner? | medical | glucose_query | 晚餐时段 CGM 趋势 |
| G4 | My reading was 4.1 this morning, should I be worried? | medical | glucose_query | 接近低血糖阈值，安全提示 |

---

## 模块三：药物管理

| ID | 输入 | 预期 Intent | 预期 Sub-intent | 测试亮点 |
|----|------|------------|----------------|---------|
| M1 | I forgot to take my Metformin this morning, what should I do? | medical | medication_query | RAG 漏服处理 |
| M2 | Metformin is making me feel nauseous, is that normal? | medical | medication_query | RAG 副作用知识 |
| M3 | Can I take Metformin with my blood pressure medicine? | medical | medication_query | 药物相互作用 |
| M4 | Should I take Metformin before or after meals? | medical | medication_query | 服药时间建议 |

---

## 模块四：情绪 + 医疗（Hybrid Agent）

| ID | 输入 | 预期 Intent | 预期 Sub-intent | 测试亮点 |
|----|------|------------|----------------|---------|
| H1 | I'm feeling really down today, my daughter hasn't called. Also my blood sugar has been high all week. | hybrid | glucose_query | 情绪摘要 + CGM 双路融合 |
| H2 | I'm so stressed and anxious, I don't know if I'm taking my medication correctly. | hybrid | medication_query | fearful 情绪 + 医疗建议 |
| H3 | Managing diabetes alone is so tiring, and I keep forgetting to eat on time. | hybrid | general_medical | sad 情绪 + 独居背景 |
| H4 | I feel scared every time I check my blood sugar because the numbers are always too high. | hybrid | glucose_query | fearful + CGM 数据 |

---

## 模块五：情绪陪伴（Companion Agent）

| ID | 输入 | 预期 Intent | 预期 Sub-intent | 测试亮点 |
|----|------|------------|----------------|---------|
| C1 | I feel so lonely living alone, my daughter is far away in Australia. | companion | - | 长期情绪历史（近3天 sad）呼应 |
| C2 | Good morning! I just came back from my walk, feeling good today. | companion | - | 积极情绪，结合运动记录 |
| C3 | I'm so tired of watching what I eat every single day. | companion | - | 慢性病疲倦感 |
| C4 | Thank you for always being here for me. | companion | - | 闲聊 / 感谢 |

---

## 模块六：并发症与症状

| ID | 输入 | 预期 Intent | 预期 Sub-intent | 测试亮点 |
|----|------|------------|----------------|---------|
| S1 | I feel dizzy every time I stand up after sitting. Is this low blood sugar? | medical | complication_query | RAG 体位性低血压 vs 低血糖鉴别 |
| S2 | My feet feel numb and tingly sometimes, is that related to diabetes? | medical | complication_query | RAG 糖尿病周围神经病变 |
| S3 | I have a small cut on my foot that's not healing well. | medical | complication_query | RAG 糖尿病足护理 |
| S4 | I've been feeling very tired lately even after sleeping well. | medical | complication_query | 疲劳与血糖控制关联 |

---

## 模块七：运动建议

| ID | 输入 | 预期 Intent | 预期 Sub-intent | 测试亮点 |
|----|------|------------|----------------|---------|
| E1 | Is it safe to exercise when my blood sugar is 12? | medical | exercise_advice | CGM 数据 + RAG 运动安全阈值 |
| E2 | What kind of exercise is best for a 68-year-old diabetic? | medical | exercise_advice | 年龄 + 病情个性化建议 |
| E3 | My glucose dropped to 4.2 during my morning walk, what should I do? | medical | exercise_advice | 运动低血糖处理 |

---

## 模块八：危机检测

| ID | 输入 | 预期 Intent | 预期 Sub-intent | 测试亮点 |
|----|------|------------|----------------|---------|
| CR1 | I feel like giving up on my treatment, what's the point anymore. | crisis | - | 危机 Agent 触发，固定响应 |
| CR2 | Sometimes I wonder if it would be easier to just stop taking my medication. | crisis | - | 隐式危机信号识别 |

---

## 模块九：本地医疗资源（CHAS）

| ID | 输入 | 预期 Intent | 预期 Sub-intent | 测试亮点 |
|----|------|------------|----------------|---------|
| L1 | What is CHAS and can I use it for my diabetes checkup? | medical | general_medical | RAG 新加坡 CHAS 政策知识 |
| L2 | Where can I do a free health screening in Singapore? | medical | general_medical | RAG 本地医疗资源 |

---

**总计：31 个测试用例**（不含图片识别，需实际图片文件）
