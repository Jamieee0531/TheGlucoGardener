# Task Page Frontend Design Spec

> Date: 2026-03-15 | Branch: bailey-latest

## Goal

Build the Task page as a pure frontend demo with interactive card stack, task completion flow, and point tracking. No backend integration — all state is local React state with mock data.

## Tech Stack

- Next.js 14 (App Router), Tailwind CSS, React useState
- Single file: `app/task/page.js`
- Reuses existing `TopBar` component

## Data Model

```js
const TASKS = [
  {
    id: "move",
    title: "Move a little today",
    emoji: "🏃",
    color: "#a8cce8",       // blue
    description: "Moving your body helps support stable glucose.",
    logType: "none",        // no action button, not completable
    completable: false,
    extraInfo: "Step count: 1234/8000",
    completedLabel: null,
  },
  {
    id: "meals",
    title: "Log your meals",
    emoji: "🍽",
    color: "#a8cce8",       // blue
    description: "Small notes today, better insights tomorrow.",
    logType: "photo",       // opens camera/gallery
    completable: true,
    completedLabel: "Meal Logged!",
  },
  {
    id: "body",
    title: "Body check-in",
    emoji: "✏️",
    color: "#f0c4a8",       // orange
    description: "Tracking your waist helps monitor metabolic health.",
    logType: "form",        // opens waist/weight input
    completable: true,
    completedLabel: "Checked In!",
  },
  {
    id: "sunset",
    title: "Sunset chaser",
    emoji: "🌅",
    color: "#f0b8c0",       // pink
    description: "Personalized quest: Take a brisk walk at West Coast Park and capture the sunset.",
    logType: "photo",       // opens camera/gallery
    completable: true,
    completedLabel: "Logged!",
  },
];
```

## React State

```js
const [expandedId, setExpandedId] = useState("sunset");   // default: last card expanded
const [completedTasks, setCompletedTasks] = useState(new Set());
const [showPhotoModal, setShowPhotoModal] = useState(false);
const [activeTaskId, setActiveTaskId] = useState(null);    // which task triggered modal
const [showBodyModal, setShowBodyModal] = useState(false);
const [bodyForm, setBodyForm] = useState({ waist: "", weight: "" });
```

Constants:
- `MOCK_BASE_PTS = 2000` — mock pre-existing lifetime points
- `PTS_PER_TASK = 10`
- `MAX_DAILY_PTS = 40` — max daily points (4 completable tasks * 10)
- `MAX_PLANT_PTS = 100` — max plant growth points (accumulates across days in real app; same formula for demo)

Derived:
- `completedCount = tasks.filter(t => t.completable && completedTasks.has(t.id)).length`
- `dailyPts = completedCount * PTS_PER_TASK`
- `plantPts = completedCount * PTS_PER_TASK`
- `totalPts = MOCK_BASE_PTS + completedCount * PTS_PER_TASK`

Note: `dailyPts` and `plantPts` use the same formula in this demo. In the real app, `plantPts` would accumulate across multiple days while `dailyPts` resets daily.

## Layout

### Card Stack (top half)

Four task cards stacked vertically with slight overlap (~-10px margin between cards).

**Collapsed card** (~60px height):
- Title (bold, italic, white) + emoji, left-aligned
- White circle, right-aligned
- If completed: title has strikethrough, circle replaced by "10 pt earned!" (pink text)
- Rounded corners (20px), background = task color

**Expanded card** (~180px height):
- Same header as collapsed
- Description text (white, smaller)
- Action button: "Log Here" (pill button, slightly darker shade of card color)
- If completed: description has strikethrough, button turns green with completed label

**Interaction rules**:
- Card 4 (sunset) is expanded by default and stays open regardless of other cards — it never collapses. Multiple cards can be visible at the same time (card 4 + one of cards 1-3).
- Cards 1-3: click to expand; clicking another card among 1-3 collapses the previously expanded one (accordion within cards 1-3 only).
- Expand/collapse uses CSS transition (height + opacity, ~300ms ease)
- Expanded cards push content below them down; if content overflows, it overlaps the stats section

### Stats Section (bottom half)

Left side:
- "Daily task completed" label + bold `{dailyPts}` / 40 pts + progress bar (light blue / gray)
- "Plant growth progress" label + bold `{plantPts}` / 100 pts + progress bar (light green / gray)
- "Total pts" label + bold `{totalPts}pts`

Right side:
- flower.jpg illustration

## Completion Flows

### Photo tasks (meals, sunset)

1. User clicks "Log Here"
2. Modal appears: "Open Camera" / "Open Gallery" / "Cancel"
3. Selecting camera → `<input capture="environment">`, selecting gallery → `<input accept="image/*">`
4. Task marked complete when file input `onChange` fires with a non-empty file. No confirmation step. Modal closes.
5. Image is NOT stored or sent anywhere

### Form task (body)

1. User clicks "Log Here"
2. Modal appears with two input fields: "Waist (cm)" and "Weight (kg)"
3. User fills in values and clicks "Submit"
4. Submit button is disabled when either field is empty. Task marked completed on submit, modal closes
5. Data is NOT stored or sent anywhere

### No-action task (move)

- No "Log Here" button
- Shows "Step count: 1234/8000" as static text
- Cannot be completed via UI

### On completion (all tasks)

1. Title text gets strikethrough (`line-through`)
2. Description text gets strikethrough
3. White circle disappears → "10 pt earned!" (pink, italic) appears in same position
4. "Log Here" button → green background + completed label text
5. `completedTasks` state updated → stats section re-renders with new point values
6. Completed action buttons are non-interactive (disabled)

## Modals

### Photo Modal (ActionSheet style)

- Overlay backdrop
- White bottom sheet with rounded top corners
- Three options: "Open Camera", "Open Gallery", "Cancel"
- Same style as Chat page's ActionSheet

### Body Check-in Modal

- Overlay backdrop
- Centered white card with rounded corners
- Title: "Body Check-in"
- Two input fields: "Waist (cm)", "Weight (kg)" — number inputs
- "Submit" button (orange, matching body card color)
- "Cancel" text button

## Design Tokens

| Token | Value |
|-------|-------|
| Background | `#FFF5EE` cream |
| Card blue | `#a8cce8` |
| Card orange | `#f0c4a8` |
| Card pink | `#f0b8c0` |
| Log Here blue | `#7bb5e0` |
| Log Here orange | `#e8a878` |
| Log Here pink | `#e89098` |
| Completed button | `#8bc34a` green |
| Earned text | `#ff6b8a` pink |
| Progress blue | `#b8e6e8` |
| Progress green | `#c8e6a0` |
| Card border-radius | 20px |
| Card collapsed height | ~60px |
| Card expanded height | ~180px |
| Transition | 300ms ease |

## File Structure

```
frontend/src/app/task/page.js    — single file, all logic + UI
```

No new components needed. Reuses existing `TopBar` component.

## Not In Scope

- Backend API integration
- Persistent data storage
- Cross-page state sharing (points don't affect Home page)
- Move task completion logic (step counting)
- Image upload/storage

## Acceptance Criteria

- [ ] All 4 cards render with correct colors and content
- [ ] Cards 1-3 expand/collapse with animation (accordion within 1-3)
- [ ] Card 4 (sunset) defaults to expanded and never collapses
- [ ] "Log Here" on photo tasks opens camera/gallery modal
- [ ] "Log Here" on body task opens waist/weight form
- [ ] Completing a task shows strikethrough, "10 pt earned!", green button
- [ ] Completed buttons are disabled (non-interactive)
- [ ] Stats section updates points on task completion
- [ ] Progress bars reflect current completion state
- [ ] Refreshing the page resets all state
