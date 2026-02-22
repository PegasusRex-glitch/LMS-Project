document.getElementById("profile-form").addEventListener("submit", async function (e) {
    e.preventDefault();

    const formData = new FormData(this);

    const res = await fetch("/profile", {
        method: "POST",
        body: formData
    });

    if (res.ok) {
        location.href = "/profile";
    }
});

function addSubject() {
    const name = prompt("Enter subject");
    if (!name) return;

    const existing = document.querySelectorAll('input[name="subjects"]');
    for (let input of existing) {
        if (input.value.toLowerCase() === name.toLowerCase()) {
            alert("Subject already added");
            return;
        }
    }

    const chip = document.createElement("div");
    chip.className = "subject-chip";


    chip.innerHTML = `
                <span>${name}</span>
                <button type="button" onclick="removeSubject(this)">×</button>
                <input type="hidden" name="subjects" value="${name}">
            `;

    document.querySelector(".subject-chips").appendChild(chip);
}

function removeSubject(btn) {
    btn.parentElement.remove();
}

function uploadProfilePhoto() {
    document.getElementById('profile-upload').click();
}

document.getElementById('profile-upload').addEventListener("change", async function () {
    const file = this.files[0];
    if (!file) return;

    const reader = new FileReader();
    reader.onload = function (e) {
        document.getElementById("profile-pic").src = e.target.result;
    };
    reader.readAsDataURL(file);

    const formData = new FormData();
    formData.append("file", file);

    res = await fetch("/profile/upload-photo", {
        method: "POST",
        body: formData
    });
    if (!res.ok) {
        alert("Failed to upload photo");
    }
});