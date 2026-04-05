# seed_user_002 数据集设计 — Marcus 的故事

> 本文档描述 user_002 (Marcus) 的全部测试数据注入计划及组合 scenario 逻辑。
> 审核通过后据此实现 `seed_user_002.py` 和 `demo/scenarios/marcus_full_story.json`。

---

## 1. User Profile

| 字段 | 值 | 说明 |
|---|---|---|
| user_id | `user_002` | |
| name | `Marcus` | |
| birth_year | `1968` | 58 岁 (2026), warehouse supervisor |
| gender | `male` | |
| waist_cm | `92.0` | 偏高，符合 T2D 风险特征 |
| weight_kg | `85.0` | |
| height_cm | `178.0` | BMI ≈ 26.8 (overweight) |
| avatar | `avatar_2` | |
| language | `English` | |
| onboarding_completed | `True` | |

---

## 2. Weekly Patterns (每周运动计划)

剧本: "goes to the gym three to four times a week"

| day_of_week | 时间 | activity_type | 说明 |
|---|---|---|---|
| 0 (Mon) | 14:00 – 15:30 | resistance_training | |
| 2 (Wed) | 14:00 – 15:30 | resistance_training | |
| 3 (Thu) | 18:00 – 19:00 | cardio | 第 4 次, 下班后 |
| 5 (Sat) | 14:00 – 15:30 | resistance_training | **故事核心日** |

---

## 3. Known Places

| place_name | place_type | gps_lat | gps_lng | 说明 |
|---|---|---|---|---|
| Home | home | 1.3521 | 103.8198 | 新加坡中心区 |
| ActiveSG Gym | gym | 1.3200 | 103.8400 | scenario 中 GPS 坐标 |
| Warehouse | office | 1.2800 | 103.8500 | warehouse supervisor |

---

## 4. Emergency Contact

| 字段 | 值 |
|---|---|
| contact_name | `Linda` |
| phone_number | `+6591234567` |
| relationship | `family` |
| notify_on | `["hard_low_glucose", "hard_high_hr", "data_gap"]` |

剧本: "Linda's phone received an automatic notification — Marcus needs help."

---

## 5. Historical CGM Data (过去 21 天, 不含今天)

### 5.1 基线模式 (非运动时段)

每 10 分钟一条, 基于时间段的正态分布:

| 时段 | 基准 (mmol/L) | SD | 说明 |
|---|---|---|---|
| 00:00–06:59 | 5.8 | 0.3 | 空腹夜间 |
| 07:00–08:59 | 7.2 | 0.4 | 早餐后 |
| 09:00–11:59 | 6.0 | 0.3 | 上午 |
| 12:00–13:59 | 7.5 | 0.4 | 午餐后 |
| 14:00–17:59 | 6.2 | 0.3 | 下午 |
| 18:00–19:59 | 7.8 | 0.5 | 晚餐后 |
| 20:00–23:59 | 6.0 | 0.3 | 晚间 |

所有值 clamp 到 [3.5, 12.0]。

### 5.2 周六运动日特殊 CGM 模式 (关键!)

过去 3 个周六 (day_offset = 7, 14, 21 天前), 在 14:00-15:30 运动时段:

| 周六 | 运动前 13:50 | 运动中 14:30 | 运动后 15:30 | drop |
|---|---|---|---|---|
| 7 天前 | **6.20** | 5.62 | **5.30** | **0.90** |
| 14 天前 | **5.80** | 5.38 | **5.00** | **0.80** |
| 21 天前 | **6.00** | 5.50 | **5.12** | **0.88** |
| | | | **avg drop** | **0.86** |

实现方式: 在这 3 个周六的 13:00-16:00 时段, 用特殊曲线替代基线模式:
- 13:00-13:50: 从午餐后高点逐渐回落到"运动前"值
- 14:00-15:30: 线性下降 (模拟运动消耗)
- 15:30-16:00: 缓慢回升

---

## 6. Historical HR Data (过去 21 天, 不含今天)

每 10 分钟一条。

### 6.1 基线
- 静息: 65-80 bpm (random)
- GPS: Home 坐标附近 (± 0.001 随机偏移)

### 6.2 运动时段 HR (所有运动日)
- 运动期间: 125-160 bpm
- GPS: Gym 坐标附近

### 6.3 周六运动日 HR
- 14:00-15:30: 130-155 bpm, GPS 在 Gym (1.3200, 103.8400)

---

## 7. Exercise Log (过去 21 天)

按 weekly_patterns 生成, 共约 12 条:

| 类型 | 天数 | 时间 | avg_hr | calories |
|---|---|---|---|---|
| resistance_training | 每周一 | 14:00-15:30 | 130-150 | 380-440 |
| resistance_training | 每周三 | 14:00-15:30 | 130-150 | 380-440 |
| cardio | 每周四 | 18:00-19:00 | 140-160 | 300-380 |
| resistance_training | **每周六** | 14:00-15:30 | 135-155 | 390-450 |

注意: 跳过今天 (周六), 今天的运动由 scenario 实时触发。

---

## 8. Food Log (过去 7 天)

为 Agent investigator 提供饮食上下文。Marcus 是新加坡人, 饮食偏当地风格:

| meal_type | 典型 food_name | gi_level | total_calories | 时间 |
|---|---|---|---|---|
| breakfast | Kaya Toast + Kopi | medium | 320 | 07:30 |
| lunch | Chicken Rice | medium | 650 | 12:30 |
| dinner | Fish Soup Bee Hoon | low | 480 | 19:00 |
| snack | Banana | medium | 105 | 16:00 (偶尔) |

每天 3 餐 + 偶尔 snack, 7 天 ≈ 22-25 条记录。随机选取上述菜品变体。

---

## 9. Emotion Log (过去 3 天, 少量)

轻度焦虑, 符合 "slightly stubborn, driven" 人设:

| day_offset | user_input | emotion_label |
|---|---|---|
| 1 天前 | "Feeling a bit tired after the long shift" | neutral |
| 2 天前 | "Good workout today, pushed through" | positive |
| 3 天前 | "Annoyed that I had to skip lunch break" | frustrated |

---

## 10. Pipeline 聚合表

### user_glucose_daily_stats (过去 21 天)

由 CGM 数据计算, 每天一行。典型值:

| 字段 | 范围 | 说明 |
|---|---|---|
| avg_glucose | 5.8 – 6.5 | Marcus 控制尚可 |
| peak_glucose | 8.5 – 10.0 | 餐后高峰 |
| nadir_glucose | 4.5 – 5.2 | 非运动日; 运动日可到 5.0 |
| glucose_sd | 0.8 – 1.2 | |
| tir_percent | 85 – 95 | 大部分时间在范围内 |
| tbr_percent | 0 – 2 | 极少低于 3.9 |
| tar_percent | 3 – 10 | 偶尔餐后高 |
| data_points | 144 | 24h × 6/h |

### user_glucose_weekly_profile (过去 2 周)

| 字段 | 值 | 说明 |
|---|---|---|
| avg_glucose | ~6.1 | |
| cv_percent | ~18 | < 36% 稳定 |
| tir_percent | ~90 | |
| coverage_percent | ~95 | |

---

## 11. Reward Log

| 字段 | 值 | 说明 |
|---|---|---|
| total_points | 320 | 可用积分 |
| accumulated_points | 480 | 历史总积分 |
| consumed_points | 160 | 已消费 |

---

## 12. Friends

| friend_id | 说明 |
|---|---|
| user_001 | 与 user_001 互为好友 |
| user_003 | 与 user_003 互为好友 |

---

## 13. Scenario 剧本 (拆分为 3 个独立 JSON, 适合现场逐个点击演示)

### 演示顺序: A → Reset Today → B → Reset Today → C

---

### 13a. `marcus_soft_pre_exercise.json` — 运动前软触发

**演示目的**: 展示 Agent 主动推理能力 — 血糖正常但预判运动后会低。

```json
{
  "scenario_id": "marcus_soft_pre_exercise",
  "description": "Marcus arrives at gym with glucose 4.9. Agent predicts post-exercise drop to 4.04 and sends preventive nudge.",
  "prerequisite": "seed_user_002; weekly_patterns has Saturday resistance_training; DEMO_MODE=true",
  "expected_outcome": "SOFT_TRIGGER (PRE_EXERCISE_LOW_BUFFER) → Investigator → Reflector (avg_drop=0.86, projected=4.04) → Communicator push",
  "steps": [
    {
      "offset_minutes": 0,
      "endpoint": "POST /telemetry/hr",
      "body": {"heart_rate": 78, "gps_lat": 1.3200, "gps_lng": 103.8400},
      "note": "Marcus arrives at ActiveSG Gym, resting HR"
    },
    {
      "offset_minutes": 0,
      "endpoint": "POST /telemetry/cgm",
      "body": {"glucose": 4.9},
      "note": "4.9 ∈ [4.0, 5.6] + Saturday workout within 60min → SOFT_PRE_EXERCISE_LOW_BUFFER"
    }
  ]
}
```

**触发链路:**
```
HR 78 @ Gym GPS
  └─ Hard: HR < (220-58)*0.9 = 145.8 → pass

CGM 4.9
  ├─ Hard: 4.9 ≥ 3.9 → pass
  └─ Soft pre-exercise:
      ├─ 4.9 ∈ [4.0, 5.6]? YES
      ├─ Saturday (dow=5) has workout at 14:00, within 60min? YES
      └─ → enqueue Celery → LangGraph Agent
          ├─ Investigator: 查 3 次周六 exercise + 对应 CGM
          ├─ Reflector: avg_drop=0.86, projected=4.9-0.86=4.04 → SOFT_REMIND
          └─ Communicator: "Hey Marcus! Your glucose is 4.9.
              If you start resistance training, it could drop to 4.04.
              Consider a small apple or nuts beforehand. Stay safe!"
```

**现场讲解点**: 血糖 4.9 完全正常，传统系统不会报警。但 Agent 结合个人历史运动血糖下降规律，主动预判风险。

---

### 13b. `marcus_hard_low_glucose.json` — 运动中低血糖硬触发

**演示目的**: Marcus 忽略软警告，运动 7 分钟后血糖跌破 3.9，系统立即触发紧急响应。

```json
{
  "scenario_id": "marcus_hard_low_glucose",
  "description": "Marcus ignored the soft alert. 7 min into workout, glucose crashes to 3.8 → hard trigger fires, Linda notified.",
  "prerequisite": "seed_user_002; emergency_contact Linda with notify_on hard_low_glucose",
  "expected_outcome": "HARD_TRIGGER (LOW_GLUCOSE < 3.9) → EmergencyService → push + SMS + call to Linda",
  "steps": [
    {
      "offset_minutes": 0,
      "endpoint": "POST /telemetry/hr",
      "body": {"heart_rate": 138, "gps_lat": 1.3200, "gps_lng": 103.8400},
      "note": "Marcus is exercising, HR elevated"
    },
    {
      "offset_minutes": 0,
      "endpoint": "POST /telemetry/cgm",
      "body": {"glucose": 4.5},
      "note": "Glucose dropping during workout, still safe"
    },
    {
      "offset_minutes": 3,
      "endpoint": "POST /telemetry/hr",
      "body": {"heart_rate": 155, "gps_lat": 1.3200, "gps_lng": 103.8400},
      "note": "High exertion, mid-rep"
    },
    {
      "offset_minutes": 3,
      "endpoint": "POST /telemetry/cgm",
      "body": {"glucose": 3.8},
      "note": "CRITICAL: < 3.9 → HARD TRIGGER → Emergency response"
    }
  ]
}
```

**触发链路:**
```
Step 1-2 (HR 138, CGM 4.5)
  ├─ Hard: 4.5 ≥ 3.9 → pass
  └─ Soft slope: 只有 1 个新点, 不够 → pass

Step 3-4 (HR 155, CGM 3.8)
  ├─ Hard: 3.8 < 3.9 → HARD_TRIGGER!
  │   └─ EmergencyService.fire("user_002", "hard_low_glucose")
  │       ├─ App push: "CRITICAL: Blood glucose 3.8. STOP NOW."
  │       ├─ SMS → Linda (+6591234567)
  │       └─ Twilio voice call → Linda
  └─ intervention_log: trigger_type=hard_low_glucose, display_label="Low Glucose"
```

**现场讲解点**: 硬触发零延迟、无 LLM 推理，直接行动。两层警报形成对比 — soft 先思考再行动, hard 直接行动不犹豫。

---

### 13c. `marcus_no_trigger.json` — 正常读数无触发 (可选)

**演示目的**: 对照组, 证明系统不会乱报警。

```json
{
  "scenario_id": "marcus_no_trigger",
  "description": "Normal Saturday readings — glucose safe, HR normal. System correctly stays silent.",
  "prerequisite": "seed_user_002",
  "expected_outcome": "No trigger fired. No notifications. No intervention_log entries.",
  "steps": [
    {
      "offset_minutes": 0,
      "endpoint": "POST /telemetry/hr",
      "body": {"heart_rate": 72, "gps_lat": 1.3521, "gps_lng": 103.8198},
      "note": "Marcus at home, resting"
    },
    {
      "offset_minutes": 0,
      "endpoint": "POST /telemetry/cgm",
      "body": {"glucose": 6.5},
      "note": "6.5 — well within safe range, no pre-exercise concern"
    }
  ]
}
```

**现场讲解点**: 6.5 远高于 5.6 上限, 即使运动前也不会触发软警报。系统安静 = 系统正常。

---

### 现场演示流程建议

| 步骤 | 操作 | 预期效果 | 讲解 |
|---|---|---|---|
| 1 | 选择 `marcus_soft_pre_exercise.json`, 点 ▶ Play | Agent 30s 内返回 soft intervention | "血糖正常但系统主动预警" |
| 2 | 等 Agent Interventions 表出现推送文案 | intervention_log 显示 soft_pre_exercise | 展示 agent_decision 和 message_sent |
| 3 | 点 🗑️ Reset Today | 清除今天数据 | "Marcus 忽略了这个警告..." |
| 4 | 选择 `marcus_hard_low_glucose.json`, 点 ▶ Play | 3s 内出现 hard trigger | "7 分钟后, 血糖跌破 3.9" |
| 5 | intervention_log 显示 hard_low_glucose | 紧急推送 + Linda 收到通知 | "两层警报, soft 思考, hard 行动" |
| 6 | (可选) Reset → `marcus_no_trigger.json` | 无任何触发 | "正常时系统保持安静" |

---

## 14. Scenario 文件清单

| 文件 | 用途 |
|---|---|
| `demo/scenarios/marcus_soft_pre_exercise.json` | 剧本 A: 运动前软触发 |
| `demo/scenarios/marcus_hard_low_glucose.json` | 剧本 B: 运动中硬触发 |
| `demo/scenarios/marcus_no_trigger.json` | 剧本 C: 正常对照 (可选) |

同步更新 `ScenarioPlayer.jsx` SCENARIOS 数组追加以上 3 个文件名。

---

## 15. 数据量汇总

| 表 | 预计行数 |
|---|---|
| users | 1 |
| user_weekly_patterns | 4 |
| user_known_places | 3 |
| user_emergency_contacts | 1 |
| user_cgm_log | ~3,024 (21 天 × 144/天) |
| user_hr_log | ~3,024 |
| user_exercise_log | ~12 (3 周 × 4 次/周) |
| user_food_log | ~23 (7 天 × 3-4 餐) |
| user_emotion_log | 3 |
| user_glucose_daily_stats | 21 |
| user_glucose_weekly_profile | 2 |
| reward_log | 1 |
| user_friends | 2 |
| **总计** | **~6,120** |
