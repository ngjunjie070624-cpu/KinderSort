# KinderSort — Teacher's Guide

*How to sort your students' event photos automatically*

---

## 1. Introduction

KinderSort AI is a desktop app that helps kindergarten teachers organise classroom event photos. It looks at each photo, finds your students' faces, and automatically copies each photo into the correct student's folder — so you don't have to sort hundreds of photos by hand.

**What it does:**
- Detects faces in your event photos
- Compares them to reference photos you provide
- Copies matching photos into a folder for each student
- Puts photos it cannot match into a special `_unmatched` folder

**Important things to know:**
- Your **original photos are never moved or deleted** — KinderSort only **copies** files.
- **One photo can appear in multiple folders** — for example, a group photo with three students will be copied to all three students' folders.
- The app runs on your computer only (**no cloud upload**). After the first setup, sorting works offline.

---

## 2. System Requirements

| Requirement | Detail |
|---|---|
| Operating system | Windows 10 or Windows 11 |
| Hardware | Any normal classroom laptop or PC — **no graphics card (GPU) required** |
| Disk space | About 2 GB free (for the app and AI models) |
| Internet | Needed **once** the very first time you run the app (to download AI models). After that, sorting works offline. |

**Supported photo formats:** `.jpg`, `.jpeg`, `.png`, `.bmp`, `.webp`

---

## 3. Launching the Application

1. Extract the downloaded ZIP file if you have not already done so.
2. Double-click **`KinderSort.exe`** to open the app.

![App on launch — window visible while AI models load in the background](guidebook_assets/01_launch.png)

*📷 **Screenshot placeholder:** Capture the app immediately after launch, showing the message **"Loading AI models..."** in the Progress area and the **Start Sorting** button greyed out (disabled).*

**What you will see:**
- The window title reads **"KinderSort AI — Face Recognition & Photo Sorting System"**.
- The app window opens right away.
- A message **"Loading AI models..."** appears while the app prepares in the background.
- The green **▶ Start Sorting** button is **greyed out** until loading finishes.

**Wait until you see:**
- The status message changes to **"Ready"**.
- The **Status** panel (top right of the Status card) shows **"Ready"**.
- The **▶ Start Sorting** button becomes clickable.

This usually takes 30 seconds to a few minutes, depending on your computer. You can use the **Appearance** toggle (Light / Dark) in the top-right corner to switch the display theme while you wait.

> ⚠️ **If you see "Failed to load AI models"** — close the app, check that you have an internet connection (needed on first run), and try again. See [Common Errors and Solutions](#11-common-errors-and-solutions).

---

## 4. Selecting the Reference Folder

The **Reference Folder** holds one clear photo of each student so KinderSort knows what they look like.

**How to prepare this folder:**
- Put one photo per student in the folder.
- Name each photo with the student's name — for example: `Ali.jpg`, `Siti.png`, `Kumar.jpeg`.
- Use a clear, front-facing photo with good lighting and a visible face.
- You can also create a **subfolder** for a student with several reference photos — for example, `Kumar/Kumar_smiling.jpg` and `Kumar/Kumar_side.jpg`.

**In the app:**
1. Find the **📁 Reference Folder** card.
2. Click the **Browse** button on the right.
3. Navigate to your reference photos folder.
4. Click **Select Folder**.

![Reference folder selected](guidebook_assets/02_reference_selected.png)

*📷 **Screenshot placeholder:** Show the Reference Folder path filled in after browsing.*

The folder path will appear in the text box. The card description reads: *"One clear photo per student, named by student name."*

---

## 5. Selecting the Classroom Folder

The **Classroom Folder** contains your event photos — the photos you want to sort.

**Recommended folder structure:**
```
Classroom/
    Sports_Day/
        IMG_001.jpg
        IMG_002.jpg
    Concert/
        IMG_003.jpg
    Field_Trip/
        IMG_004.jpg
```

- Create one **subfolder per event** (e.g. `Sports_Day`, `Concert`).
- Place the event photos inside each subfolder.

> **Tip:** If your photos are all in one folder with no subfolders, KinderSort can still process them — but using event subfolders helps keep results organised and adds the event name to each output filename.

**In the app:**
1. Find the **🏫 Classroom Folder** card.
2. Click **Browse**.
3. Navigate to the folder that **contains your event subfolders** (not an individual event folder, unless all photos are in one place).
4. Click **Select Folder**.

![Classroom folder selected](guidebook_assets/03_events_selected.png)

*📷 **Screenshot placeholder:** Show the Classroom Folder path filled in after browsing.*

The card description reads: *"Event photo subfolders to be sorted (e.g. Sports_Day, Concert)."*

---

## 6. Selecting the Output Folder

The **Output Folder** is where KinderSort will save the sorted results.

**How to prepare:**
- Create a new empty folder anywhere on your computer — for example, `Sorted_Photos_2026`.
- KinderSort will create student folders and an `_unmatched` folder inside it automatically.

**In the app:**
1. Find the **📤 Output Folder** card.
2. Click **Browse**.
3. Navigate to your empty output folder.
4. Click **Select Folder**.

![All three folders selected and ready to sort](guidebook_assets/04_all_folders_set.png)

*📷 **Screenshot placeholder:** Show all three folder paths filled in, status **"Ready"**, and the **▶ Start Sorting** button enabled.*

The card description reads: *"Where sorted student folders and the log file will be written."*

When all three folders are selected and the app shows **"Ready"**, you can begin sorting.

---

## 7. Starting the Sorting Process

1. Make sure all three folders are selected.
2. Make sure the status shows **"Ready"** (not "Loading AI models...").
3. Click the green **▶ Start Sorting** button.

**What happens next:**
1. KinderSort first loads your reference photos and learns each student's face. The status will show **"Loading references"** and display each student's name as it is processed.
2. If any reference photo has no detectable face, a warning will appear listing those students. They will be skipped during sorting — replace their reference photos and run again if needed.
3. KinderSort then processes each event photo. The status changes to **"Sorting photos"**.

You can click **Cancel** at any time to stop. Photos already processed will be kept; the rest will not be processed.

> ⏱️ Processing time depends on how many photos you have and your computer speed. Face recognition uses your computer's processor (CPU) — please be patient and let it finish.

---

## 8. Understanding the Progress Display

While sorting runs, several parts of the screen update in real time.

![Sorting in progress](guidebook_assets/05_sorting_in_progress.png)

*📷 **Screenshot placeholder:** Capture the app mid-sort showing the progress bar, status panel, and System Performance panel populated with live numbers.*

### Progress card

| Element | What it shows |
|---|---|
| **Progress** bar | How far through the event photos KinderSort has got (0% to 100%) |
| **Percentage** (right of Progress) | Same progress as a number, e.g. `45%` |
| **Current file line** | The photo being processed right now, e.g. `Current: IMG_012.jpg` |
| **Remaining line** | How many photos are left, e.g. `8 remaining` |
| **Status line** (bottom) | A short message — e.g. `[12/20] IMG_012.jpg` or `Loading reference photos…` |

### Status panel

| Element | What it shows |
|---|---|
| **Phase** (top right) | Current stage — e.g. `Loading references`, `Sorting photos`, `Complete` |
| **Faces Detected** | Total faces found across all event photos so far |
| **Matched** | Photos successfully matched to at least one student |
| **Unmatched** | Photos sent to the `_unmatched` folder |
| **Processing Time** | How long the current run has been going (minutes and seconds) |

---

## 9. Understanding the Performance Panel

The **System Performance** panel shows how much of your computer's resources KinderSort is using during a sort run. You do not need to change anything here — it is for your information.

| Metric | What it means |
|---|---|
| **Current CPU Usage** | How much of your computer's processing power KinderSort is using right now (shown as 0–100%) |
| **Average CPU Usage** | Average processing power used throughout the run |
| **Current Memory Usage** | How much memory (RAM) KinderSort is using right now, in MB |
| **Peak Memory Usage** | The highest memory usage reached during the run |
| **Average Memory Usage** | Average memory used throughout the run |
| **Total Processing Time** | Total seconds elapsed since you clicked Start |
| **Average Time per Image** | Average seconds spent on each event photo |
| **Images Processed** | Number of event photos completed so far |

These numbers also appear in the **Run Summary** box when sorting finishes.

---

## 10. Viewing Matched and Unmatched Results

When sorting is complete, the **Run Summary** box at the bottom of the app shows a text report.

![Sorting complete](guidebook_assets/06_sorting_complete.png)

*📷 **Screenshot placeholder:** Capture the completed run showing Run Summary filled in, Status phase **"Complete"**, and final counts in the Status panel.*

**The summary includes:**
- **Total images found** — how many event photos were scanned
- **Faces detected** — total faces found across all photos
- **Matched (sorted)** — photos placed into student folders
- **Unmatched** — photos that could not be matched
- **Skipped (errors)** — photos that could not be opened
- **Performance figures** — CPU, memory, and timing statistics

Open your **Output Folder** in File Explorer to see the results:

```
Output/
    Ali/
        Sports_Day__IMG_001.jpg
        Concert__IMG_045.jpg
    Siti/
        Sports_Day__IMG_001.jpg       ← same group photo, copied here too
        Field_Trip__IMG_023.jpg
    Kumar/
        Concert__IMG_012.jpg
    _unmatched/
        blurry_photo.jpg
        background_only.jpg
    kindersort_log.txt
```

| Folder / file | Contents |
|---|---|
| **`<StudentName>/`** | All photos where that student's face was recognised |
| **`_unmatched/`** | Photos with no detectable face, or faces that did not match any student (e.g. teachers, parents, blurry shots) |
| **`kindersort_log.txt`** | A detailed record of everything KinderSort did — useful if something looks wrong |

**About the filenames:** Photos are named with the event folder as a prefix — for example, `Sports_Day__IMG_001.jpg` — so you always know which event each photo came from.

---

## 11. Common Errors and Solutions

### "Loading AI models..." never finishes, or "Failed to load AI models"

**Cause:** The app could not load its AI components — often because the first-run model download needs internet.

**Fix:**
1. Check your internet connection.
2. Close and reopen KinderSort.
3. Wait a few minutes — the first download is about 300 MB.
4. If the problem continues, restart your computer and try again.

---

### "Missing folders" when clicking Start Sorting

**Cause:** One or more of the three folder fields is empty.

**Fix:** Select all three folders — Reference, Classroom, and Output — before clicking **▶ Start Sorting**.

---

### "Invalid folder" — Reference or Classroom folder does not exist

**Cause:** The folder path is wrong, or the folder was moved or deleted.

**Fix:** Click **Browse** again and re-select the correct folder.

---

### "Reference photos without faces" warning

**Cause:** One or more reference photos do not contain a clear, detectable face.

**Fix:**
1. Note which student names are listed in the warning.
2. Replace those reference photos with clearer, front-facing photos (good lighting, plain background, no sunglasses).
3. Run sorting again.

---

### "No student faces could be loaded"

**Cause:** None of the reference photos produced a usable face.

**Fix:** Check your Reference Folder — make sure photos are named correctly, faces are clearly visible, and files are in a supported format (`.jpg`, `.png`, etc.).

---

### "No images found" after sorting

**Cause:** KinderSort did not find any photos in the Classroom Folder.

**Fix:**
1. Check that your event photos are inside subfolders of the Classroom Folder (e.g. `Classroom/Sports_Day/photos…`).
2. Make sure photos use a supported format (`.jpg`, `.jpeg`, `.png`, `.bmp`, `.webp`).
3. Re-select the Classroom Folder if you pointed to the wrong location.

---

### Many photos end up in `_unmatched`

**Possible causes:**
1. Reference photos are unclear or outdated
2. Event photos are blurry, very dark, or taken from far away
3. Students are wearing face masks, large hats, or facing away from the camera

**Fix:**
1. Use better reference photos first — clear, recent, front-facing.
2. If a reference photo has several people in it, KinderSort uses the **largest face** — try cropping to show only the student.
3. Very difficult event photos may simply not be matchable.

---

### Progress bar seems stuck

**Cause:** Face recognition is processor-intensive — the app may be working on a large or complex photo.

**Fix:**
1. Watch the **Current file** line and **Processing Time** — if the filename changes or time increases, the app is still working.
2. Check **Images Processed** in the System Performance panel — if the number is going up, sorting is progressing.
3. Wait patiently. A large batch can take many minutes on an older computer.

---

### Output photos have long names like `Sports_Day__IMG_001.jpg`

This is **normal**. The event folder name is added as a prefix so you always know which event each photo came from.

---

## 12. Frequently Asked Questions

### Do I need to install Python or any other software?

**No.** If you are using the packaged `KinderSort.exe`, just double-click it. No Python or technical setup is required.

---

### Does KinderSort need the internet every time?

**No.** Internet is only needed the **first time** you run the app, to download AI models (about 300 MB). After that, sorting works fully offline.

---

### Will KinderSort delete or move my original photos?

**No.** KinderSort only **copies** photos to the Output Folder. Your original reference photos and event photos stay exactly where they are.

---

### Can one photo go into more than one student's folder?

**Yes.** Group photos are copied to every student folder where a matching face was found.

---

### Can I use more than one reference photo per student?

**Yes.** Create a subfolder named after the student inside your Reference Folder and put several photos inside — for example, `Reference/Kumar/photo1.jpg` and `Reference/Kumar/photo2.jpg`.

---

### What goes in the `_unmatched` folder?

Photos where:
- No face was detected (landscapes, blurry shots, etc.)
- A face was detected but did not match any student (teachers, parents, unknown people)
- The photo could not be processed for matching

---

### Can I stop sorting halfway through?

**Yes.** Click **Cancel**. Photos already processed and copied will be kept. The summary will show **"Sorting cancelled."**

---

### What is `kindersort_log.txt`?

A detailed text log saved in your Output Folder. It records every photo processed, every match, and every problem. You normally do not need to read it, but it is helpful if you need to understand why a particular photo was unmatched.

---

### Can I switch between Light and Dark mode?

**Yes.** Use the **Appearance** toggle (Light / Dark) in the top-right corner of the app window. This only changes how the app looks — it does not affect sorting.

---

### How do I get better matching results?

1. Use clear, recent, front-facing reference photos — good lighting, no sunglasses.
2. One student per reference photo works best (or use a subfolder with several angles).
3. Avoid very blurry or dark event photos where possible.
4. Re-run with improved reference photos if too many results land in `_unmatched`.

---

*KinderSort AI — Face Recognition & Photo Sorting System*
