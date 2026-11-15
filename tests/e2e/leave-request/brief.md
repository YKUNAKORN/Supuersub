# The scenario: Restday, a leave request app

The request the walk-through starts from, as a user would type it. The user writes in
Thai, so every skill replies in Thai and the visible text in the artifacts is Thai;
identifiers stay ASCII. See `docs/e2e-walkthrough.md` for what each skill produced and
what was checked.

> ทีมเรามี 15 คน อยากได้แอป Power Apps สำหรับยื่นใบลา: พนักงานกรอกประเภทการลา
> วันเริ่ม วันสิ้นสุด เหตุผล และอีเมลหัวหน้าที่อนุมัติ แล้วเห็นรายการใบลาของตัวเองพร้อมสถานะ
> (รออนุมัติ / อนุมัติ / ไม่อนุมัติ) เก็บข้อมูลใน SharePoint list และพอยื่นแล้วให้ส่งอีเมลแจ้งหัวหน้า
> ยังไม่มี design system เริ่มจากศูนย์ได้เลย ใช้บนคอมพิวเตอร์เป็นหลัก

In English: a 15-person team wants a Power Apps app to file leave requests. An employee
enters the leave type, start date, end date, reason and the approver's e-mail, then sees
their own requests with a status (pending, approved, rejected). Data lives in a
SharePoint list, and submitting sends the approver an e-mail. No design system yet;
desktop use.

Answers given to the skills' questions (one round each):

- **design-md**: target `power-apps`; calm and plain, one green action colour; no brand
  fonts; light only; status must not rely on colour alone.
- **mock-ui**: two screens are enough (my requests, new request); no detail screen yet.
- **create-list**: one list; the approver is typed as an e-mail address for now, not a
  Person column; the status is set by the approver later, by hand.
- **create-flow**: one flow; the approver gets an e-mail with the request in it. The app
  does not call it yet, so a manual (button) trigger is fine for the first version.
