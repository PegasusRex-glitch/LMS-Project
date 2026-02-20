const express = require("express");
const nodemailer = require("nodemailer");

const app = express();
app.use(express.json());

const transporter = nodemailer.createTransport({
  service: "gmail",
  auth: {
    user: process.env.USER,
    pass: process.env.PASS,
  },
});

app.post("/send-email", async (req, res) => {
  const { to, subject, text } = req.body;

  if (!to || !subject || !text) {
    console.log("Missing required email info!");
    return res.status(400).json({ error: "Missing email fields" });
  }

  try {
    await transporter.sendMail({
      from: process.env.USER,
      to,
      subject,
      text,
    });

    console.log("Email sent to:", to);
    res.json({ success: true });
  } catch (error) {
    console.error("Email error:", error);
    res.status(500).json({ error: "Email failed" });
  }
});

app.listen(5000, () => {
  console.log("Email service running on port 5000");
});
