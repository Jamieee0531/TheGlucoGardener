# Plan A vs Plan B 对比

**运行时间**：2026-04-05 01:34

| ID | 输入 | Plan A Intent | Plan B Intent | Plan A Sub | Plan B Sub | A✅ | B✅ | A耗时 | B耗时 |
|----|----|----|----|----|----|----|----|----|----|
| F1 | Is char kway teow ok for me to eat?... | medical | medical | food_inquiry | food_inquiry | ✅ | ✅ | 23.4s | 7.5s |
| F2 | Can I eat nasi lemak for breakfast?... | medical | medical | food_inquiry | food_inquiry | ✅ | ✅ | 5.7s | 7.0s |
| F3 | What about roti prata, is it high G... | medical | medical | food_inquiry | food_inquiry | ✅ | ✅ | 11.0s | 8.7s |
| F4 | I had wonton noodles for dinner ton... | medical | medical | food_inquiry | food_inquiry | ✅ | ✅ | 5.4s | 7.4s |
| F5 | Is brown rice better than white ric... | medical | medical | food_inquiry | food_inquiry | ✅ | ✅ | 5.4s | 7.7s |
| G1 | My glucose reading is 9.5 after lun... | medical | medical | food_inquiry | glucose_query | ⚠️ | ✅ | 6.1s | 8.0s |
| G2 | What has my blood sugar been like t... | medical | medical | glucose_query | glucose_query | ✅ | ✅ | 6.4s | 8.7s |
| G3 | Why does my sugar always go high af... | medical | medical | food_inquiry | food_inquiry | ⚠️ | ⚠️ | 6.1s | 7.7s |
| G4 | My reading was 4.1 this morning, sh... | medical | medical | glucose_query | glucose_query | ✅ | ✅ | 13.5s | 9.7s |
| M1 | I forgot to take my Metformin this ... | medical | medical | medication_query | medication_query | ✅ | ✅ | 8.7s | 7.2s |
| M2 | Metformin is making me feel nauseou... | medical | medical | medication_query | medication_query | ✅ | ✅ | 6.1s | 6.9s |
| M3 | Can I take Metformin with my blood ... | medical | medical | medication_query | medication_query | ✅ | ✅ | 6.5s | 6.7s |
| M4 | Should I take Metformin before or a... | medical | medical | medication_query | medication_query | ✅ | ✅ | 8.8s | 6.7s |
| H1 | I'm feeling really down today, my d... | hybrid | companion | complication_query | - | ⚠️ | ⚠️ | 6.3s | 6.5s |
| H2 | I'm so stressed and anxious, I don'... | companion | medical | - | medication_query | ⚠️ | ⚠️ | 3.0s | 9.7s |
| H3 | Managing diabetes alone is so tirin... | companion | companion | - | - | ⚠️ | ⚠️ | 3.5s | 5.8s |
| H4 | I feel scared every time I check my... | medical | medical | glucose_query | glucose_query | ⚠️ | ⚠️ | 7.6s | 9.1s |
| C1 | I feel so lonely living alone, my d... | companion | companion | - | - | ✅ | ✅ | 4.6s | 6.5s |
| C2 | Good morning! I just came back from... | companion | companion | - | - | ✅ | ✅ | 4.3s | 5.4s |
| C3 | I'm so tired of watching what I eat... | companion | companion | - | - | ✅ | ✅ | 3.7s | 7.0s |
| C4 | Thank you for always being here for... | companion | companion | - | - | ✅ | ✅ | 7.3s | 5.6s |
| S1 | I feel dizzy every time I stand up ... | medical | medical | complication_query | complication_query | ✅ | ✅ | 6.3s | 9.1s |
| S2 | My feet feel numb and tingly someti... | medical | medical | complication_query | complication_query | ✅ | ✅ | 5.9s | 8.4s |
| S3 | I have a small cut on my foot that'... | hybrid | hybrid | complication_query | complication_query | ⚠️ | ⚠️ | 5.6s | 8.0s |
| S4 | I've been feeling very tired lately... | hybrid | companion | complication_query | - | ⚠️ | ⚠️ | 6.2s | 5.6s |
| E1 | Is it safe to exercise when my bloo... | medical | medical | exercise_advice | exercise_advice | ✅ | ✅ | 5.7s | 7.1s |
| E2 | What kind of exercise is best for a... | medical | medical | exercise_advice | exercise_advice | ✅ | ✅ | 5.7s | 7.4s |
| E3 | My glucose dropped to 4.2 during my... | medical | medical | exercise_advice | glucose_query | ✅ | ⚠️ | 5.7s | 8.3s |
| CR1 | I feel like giving up on my treatme... | crisis | crisis | - | - | ✅ | ✅ | 0.5s | 2.5s |
| CR2 | Sometimes I wonder if it would be e... | crisis | crisis | - | - | ✅ | ✅ | 0.4s | 2.7s |
| L1 | What is CHAS and can I use it for m... | medical | medical | general_medical | general_medical | ✅ | ✅ | 6.3s | 8.8s |
| L2 | Where can I do a free health screen... | medical | medical | general_medical | general_medical | ✅ | ✅ | 8.1s | 9.7s |

**Plan A（Semantic Router）**：24/32 通过，平均 6.6s
**Plan B（Gemini）**：24/32 通过，平均 7.3s