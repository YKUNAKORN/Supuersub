# Restday: SharePoint lists

สถานะ: ผู้ใช้อนุมัติแล้ว · 2026-11-15 · สร้างจาก: `supersub/mockup/sitemap.json` และคำอธิบายของผู้ใช้

หนึ่ง list พอสำหรับเวอร์ชันแรก: mockup อ่านและเขียน `LeaveRequests` ที่เดียว ผู้ยื่นคือ
**Created By** ของแถว ซึ่ง SharePoint ใส่ให้เอง จึงไม่ต้องมีคอลัมน์ผู้ยื่น

## LeaveRequests (ใบลา)

| Column | Display name | finalType | importType | Required | Unique | Choices | Notes |
|---|---|---|---|---|---|---|---|
| `LeaveType` | ประเภทการลา | choice | choice | yes | no | ลาพักร้อน, ลาป่วย, ลากิจ | |
| `StartDate` | วันเริ่ม | date | datetime | yes | no | | indexed; ตั้ง Date only หลัง import |
| `EndDate` | วันสิ้นสุด | date | datetime | yes | no | | ตั้ง Date only หลัง import |
| `Reason` | เหตุผล | note | note | no | no | | |
| `ApproverEmail` | อีเมลผู้อนุมัติ | text | text | yes | no | | flow `NotifyApprover` ส่งไปที่อยู่นี้ |
| `Status` | สถานะ | choice | choice | yes | no | รออนุมัติ, อนุมัติ, ไม่อนุมัติ | indexed; ค่าเริ่มต้น รออนุมัติ |

ชื่อคอลัมน์ตรงกับ `data-field` ใน mockup ทุกตัว (`sitemap.json`: `LeaveType`, `StartDate`,
`EndDate`, `Reason`, `ApproverEmail`, `Status`)

## ความสัมพันธ์

ไม่มี lookup

## ลำดับการสร้าง

1. `LeaveRequests`

## สิ่งที่ยังไม่ได้ยืนยัน

ผู้อนุมัติเก็บเป็นอีเมล (text) ไม่ใช่ Person ตามที่ผู้ใช้เลือก เพราะ `offer-person` ยังเป็น
`unverified` และ flow ต้องการแค่ที่อยู่อีเมล ถ้าภายหลังต้องการ Person ให้สร้างคอลัมน์ใหม่เอง
