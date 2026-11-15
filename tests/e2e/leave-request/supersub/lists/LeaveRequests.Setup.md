# ใบลา (LeaveRequests)

ใบลาของพนักงาน หนึ่งแถวต่อหนึ่งใบลา ผู้ยื่นคือ Created By ของแถว

Import file: `LeaveRequests.csv`, UTF-8 with a byte-order mark. Choose **From CSV**.

| Column | เลือกชนิดในหน้า import | ตั้งค่าหลัง import (Column settings) | หมายเหตุ |
|---|---|---|---|
| LeaveType | Choice | Display name: ประเภทการลา; Choices: ลาพักร้อน; ลาป่วย; ลากิจ; Required |  |
| StartDate | Date and time (Date only, if offered) | Display name: วันเริ่ม; Date and time format: Date only; Indexed; Required | ตั้ง Date only หลัง import |
| EndDate | Date and time (Date only, if offered) | Display name: วันสิ้นสุด; Date and time format: Date only; Required | ตั้ง Date only หลัง import |
| Reason | Multiple lines of text | Display name: เหตุผล |  |
| ApproverEmail | Single line of text | Display name: อีเมลผู้อนุมัติ; Required | flow NotifyApprover ส่งอีเมลไปที่อยู่นี้ ภายหลังเปลี่ยนเป็น Person ได้ แต่ต้องสร้างคอลัมน์ใหม่เอง |
| Status | Choice | Display name: สถานะ; Choices: รออนุมัติ; อนุมัติ; ไม่อนุมัติ; Default value: รออนุมัติ; Indexed; Required | ผู้อนุมัติเปลี่ยนสถานะเองใน list |

**หลัง import:**

- ลบสามแถวตัวอย่างหลังตรวจชนิดคอลัมน์แล้ว
- เปลี่ยนชื่อที่แสดงของแต่ละคอลัมน์เป็นภาษาไทยตามตาราง
