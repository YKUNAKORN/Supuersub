# Flows: Restday

Status: ผู้ใช้อนุมัติแล้ว · 2026-11-15 · สร้างจาก: `supersub/mockup/sitemap.json`, `supersub/lists/LeaveRequests.list.json` และคำอธิบายของผู้ใช้

## ภาพรวมของระบบ

พนักงานยื่นใบลาในหน้า `scrNewLeave` ของแอป ใบลาถูกบันทึกเป็นแถวใน list `LeaveRequests`
พร้อมสถานะ รออนุมัติ แล้วผู้อนุมัติต้องได้รับอีเมลแจ้ง ผู้อนุมัติเปลี่ยนสถานะใน list เอง
flow เข้ามาทำงานเฉพาะขั้นส่งอีเมล

**สมมติฐาน** (แก้ได้ถ้าไม่ถูก):

- อีเมลผู้อนุมัติมาจากคอลัมน์ `ApproverEmail` ที่พนักงานกรอก ไม่ได้หาจากโครงสร้างองค์กร
- ใช้ Office 365 Outlook ของผู้ที่ import flow เป็นผู้ส่ง
- เวอร์ชันแรกรัน flow ด้วยปุ่มใน Power Automate เพราะ trigger แบบ Power Apps ยังเป็น
  `unattempted` ใน catalog แอปจึงยังไม่เรียก flow นี้ (ปุ่ม ส่งใบลา มี placeholder แทน)

**คำถามที่ยังเปิดอยู่**:

- ต้องการให้ flow เริ่มเองเมื่อมีแถวใหม่ใน list หรือไม่ ถ้าใช่ ต้องสร้างเองหนึ่งครั้งแล้ว export
  มา harvest เพราะ trigger ของ SharePoint ยังเป็น `unattempted`

## Inventory

| # | Flow (display name) | Name | Trigger | What it does | Connectors | Lists read / written | Called by | Status |
|---|---|---|---|---|---|---|---|---|
| 1 | Restday: แจ้งผู้อนุมัติ | `NotifyApprover` | button | ส่งอีเมลรายละเอียดใบลาให้ผู้อนุมัติ | Office 365 Outlook | ไม่อ่านไม่เขียน (ค่ามาจาก input) | `scrNewLeave` ส่งใบลา (`run-flow:NotifyApprover`), ยังเป็น placeholder | package with unverified steps |

**1 flow และเหตุผล**: ระบบมีงานอัตโนมัติงานเดียวคือแจ้งผู้อนุมัติ การเปลี่ยนสถานะทำด้วยมือใน
list จึงไม่ต้องมี flow ที่สอง

## 1. Restday: แจ้งผู้อนุมัติ (`NotifyApprover`): package with unverified steps

- **Trigger และ input**: ปุ่ม (manual); `text` (ข้อความ): ประเภทการลา; `text_1` (ข้อความ):
  ช่วงวันลา; `text_2` (ข้อความ): เหตุผล; `email` (อีเมล): อีเมลผู้อนุมัติ
- **ขั้นตอน**:
  1. ประกอบข้อความจาก input (Compose, `Build_message`)
  2. ส่งอีเมลถึงผู้อนุมัติ (Office 365 Outlook, Send an email (V2))
- **ผลลัพธ์**: ผู้อนุมัติได้อีเมลหนึ่งฉบับ
- **เมื่อล้มเหลว**: การรันขึ้นสถานะ Failed ใน run history ของ flow ผู้ที่รันเห็นเอง
- **Connection ที่ต้องเลือกตอน import**: Office 365 Outlook หนึ่ง connection
- **ตั้งค่าหลัง import**: ไม่มี placeholder
- **ยังไม่ได้ยืนยัน**: connection reference ที่ builder สร้างขึ้น (`package_connection_reference`)
