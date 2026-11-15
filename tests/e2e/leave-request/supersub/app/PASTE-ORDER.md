# ลำดับการวาง: Restday (2 หน้าจอ)

แปลงจาก `supersub/mockup/` (target `power-apps`, canvas 1366 × 768) ด้วย `create-app`
หนึ่งไฟล์ `.pa.yaml` ต่อหนึ่งหน้าจอ แต่ละไฟล์เป็น `Screens:` ที่สมบูรณ์และ lint ได้ด้วยตัวเอง:

```bash
python3 scripts/pa_lint.py --app-dir supersub/app --sitemap supersub/mockup/sitemap.json
```

ผลตอนเขียน: `VERDICT: SAFE TO PASTE` ทั้งสองไฟล์ 0 error 0 warning ไม่มีชื่อ control ซ้ำข้ามไฟล์

| # | File | Screen | ไปที่ | Action (ยังไม่ได้ต่อ) |
|---|---|---|---|---|
| 1 | `scrLeaveList.pa.yaml` | `scrLeaveList` (หน้าแรก) | `scrNewLeave`, ตัวเอง | ไม่มี |
| 2 | `scrNewLeave.pa.yaml` | `scrNewLeave` | `scrLeaveList`, ตัวเอง | `submit:LeaveRequests`, `run-flow:NotifyApprover` |

## ก่อนวาง

ไม่มีอะไรในสองไฟล์นี้ที่ยังไม่ได้ยืนยัน จึงไม่มี snippet ให้ทดสอบก่อน snippet ข้างล่างใช้
**ภายหลัง** ตอนเปลี่ยนแถวตัวอย่างเป็นข้อมูลจริง:

- `assets/test-snippets/gallery.pa.yaml` (แถวใบลาใน `scrLeaveList`)
- `assets/test-snippets/form.pa.yaml` (ฟอร์มใน `scrNewLeave`)
- `assets/test-snippets/datepicker.pa.yaml` (วันเริ่ม วันสิ้นสุด)

## วางหน้าจอ

เปิดแอปใน Power Apps Studio เพิ่ม **blank screen** เลือกหน้าจอนั้น ใช้ **Paste code** แล้ววาง
**ทั้งไฟล์**

1. วาง `scrLeaveList.pa.yaml` แล้ว `scrNewLeave.pa.yaml`
2. **วางครบทั้งสองหน้าก่อนตัดสิน error ของ `Navigate()`** ทั้งสองหน้าชี้ไปหากัน หน้าที่วางก่อน
   จึงอ้างถึงหน้าที่ยังไม่มี Studio จะ block, เตือน หรือขึ้น formula error ที่หายไปเองเมื่อวางหน้าปลายทาง
   **ยังไม่รู้** จนกว่าจะทดสอบ ให้สร้างทุกหน้าก่อนแล้วค่อยดู error
3. ตรวจชื่อหน้าจอใน tree view ต้องเป็น `scrLeaveList` และ `scrNewLeave` ถ้า Studio ตั้งชื่อเอง
   (`Screen2`) หรือเติม `_1` ให้เปลี่ยนชื่อเป็น id ในตาราง
4. ตรวจว่าไม่มีชื่อ control ลงท้าย `_1`

## ทำเองภายหลัง

- ตั้ง `scrLeaveList` เป็นหน้าแรก (ลากขึ้นบนสุดใน tree view) ไฟล์ไม่มี `App:` block
- ลบ blank screen ที่แอปใหม่มีมาแต่แรกถ้ายังว่างอยู่
- ปุ่ม ส่งใบลา มี `OnSelect` placeholder พร้อม comment บอก action `create-list` สร้าง list
  `LeaveRequests` แล้ว (`supersub/lists/`) `create-flow` สร้าง `NotifyApprover` แล้ว
  (`supersub/flows/`) การต่อทั้งสองต้องมี data source และ flow connection ซึ่ง
  `references/data-binding.md` ระบุว่า UNVERIFIED และ flow รุ่นนี้ใช้ trigger แบบปุ่ม แอปจึงยังเรียกไม่ได้

## คำถามสำหรับ Studio

บันทึกคำตอบใน test plan หัวข้อ "Multi-screen paste" (M1–M4) ด้วยหน้าจอชุดนี้ได้เช่นกัน
