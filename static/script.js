let students = [];
let attendance = {};
async function addStudent() {
    // Clear previous errors
    document.getElementById("rollNoError").textContent = "";
    document.getElementById("studentNameError").textContent = "";
    document.getElementById("classError").textContent = "";
    document.getElementById("fileError").textContent = "";

    // Get input values
    const rollNo = document.getElementById('rollNo').value.trim();
    const name = document.getElementById('studentName').value.trim();
    const className = document.getElementById('studentClass').value;
    const studentFile = document.getElementById('studentFile').files[0]; // Get selected file

    let isValid = true;

    // Validate Roll Number
    if (!rollNo || isNaN(rollNo)) {
        document.getElementById("rollNoError").textContent = "Please enter a valid roll number.";
        isValid = false;
    }

    // Validate Name
    const nameRegex = /^[a-zA-Z\s]+$/;
    if (!name || !nameRegex.test(name)) {
        document.getElementById("studentNameError").textContent = "Please enter a valid name (only letters and spaces).";
        isValid = false;
    }

    // Validate Class Selection
    if (!className) {
        document.getElementById("classError").textContent = "Please select a class.";
        isValid = false;
    }

    // **File Validation**
    if (!studentFile) {
        document.getElementById("fileError").textContent = "Please upload a file.";
        isValid = false;
    } else {
        const allowedExtensions = ["jpg", "jpeg", "png"];
        const fileExtension = studentFile.name.split('.').pop().toLowerCase();
        const maxFileSize = 2 * 1024 * 1024; // 2MB in bytes

        if (!allowedExtensions.includes(fileExtension)) {
            document.getElementById("fileError").textContent = "Invalid file type. Allowed: JPG, JPEG, PNG.";
            isValid = false;
        }

        if (studentFile.size > maxFileSize) {
            document.getElementById("fileError").textContent = "File size must be less than 2MB.";
            isValid = false;
        }
    }

    // **Check for duplicate roll number**
    if (students.some(student => student.roll_no === rollNo)) {
        document.getElementById("rollNoError").textContent = "Roll number already exists.";
        return; // Stop execution
    }

    // If all validations pass, send data to server
    if (isValid) {
        let formData = new FormData();
        formData.append("rollNo", rollNo);
        formData.append("studentName", name);
        formData.append("studentClass", className);
        formData.append("file", studentFile);

        try {
            let response = await fetch("/add-student", {
                method: "POST",
                body: formData
            });

            let data = await response.json();
            alert(data.message);
            document.getElementById("addStudentForm").reset();
        } catch (error) {
            console.error("Error:", error);
        }
    }
}

function showSection(sectionId) {
    document.querySelectorAll('.section').forEach(section => {
        section.classList.remove('active');
    });
    document.getElementById(sectionId).classList.add('active');
}

function showAddStudentModal() {
    const modal = new bootstrap.Modal(document.getElementById('addStudentModal'));
    modal.show();
}

document.getElementById('classSelect').addEventListener('change', (e) => {
    if (e.target.value) {
        updateAttendanceList(e.target.value);
    }
});

document.getElementById('attendanceDate').addEventListener('change', () => {
    const selectedClass = document.getElementById('classSelect').value;
    if (selectedClass) {
        updateAttendanceList(selectedClass);
    }
});

window.addEventListener('DOMContentLoaded', updateStudentsList);

function updateStudentsList() {
    const tbody = document.getElementById('studentsList');
    tbody.innerHTML = '';

    fetch('/get_students')
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                students = data.students;

                if (students.length === 0) {
                    tbody.innerHTML = `<tr><td colspan="4" class="text-center">No students found</td></tr>`;
                    return;
                }

                students.forEach(student => {
                    const tr = document.createElement('tr');
                    tr.innerHTML = `
                        <td>${student.roll_no}</td>
                        <td>${student.name}</td>
                        <td>${student.class}</td>
                        <td>
                            <button class="btn btn-sm btn-danger" onclick="deleteStudent('${student.roll_no}')">
                                Delete
                            </button>
                        </td>
                    `;
                    tbody.appendChild(tr);
                });

                updateDashboard();
                updateAttendanceList(document.getElementById('classSelect').value);
            } else {
                console.error("Error fetching students:", data.status);
                alert("Error fetching students. Check the console.");
            }
        })
        .catch(error => {
            console.error("Network Error:", error);
            alert("A network error occurred.");
        });
}
function updateAttendanceList(className) {
    const tbody = document.getElementById('attendanceList');
    tbody.innerHTML = '';

    fetch(`/get_attendance_list?class=${className}`) // Only fetch students
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                const studentList = data.attendance; // Renamed for clarity

                if (studentList.length === 0) {
                    tbody.innerHTML = "<tr><td colspan='2'>No students found</td></tr>";
                    return;
                }

                studentList.forEach(student => {
                    const tr = document.createElement('tr');
                    tr.innerHTML = `
                        <td>${student.roll_no}</td>
                        <td>${student.name}</td>
                        
                    `; // Removed status column
                    tbody.appendChild(tr);
                });
            } else {
                console.error("Error fetching student list:", data.message);
            }
        })
        .catch(error => {
            console.error("Error fetching students:", error);
            alert("A network error occurred while fetching students.");
        });
}
function deleteStudent(rollNo) {
    if (confirm('Are you sure you want to delete this student?')) {
        fetch('/delete_student', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ roll_no: Number(rollNo) }) // Convert to number
        })
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                alert(data.status);
                updateStudentsList(); // Refresh list
                updateDashboard();
            } else {
                alert("Error deleting student: " + data.status);
                console.error("Delete error:", data);
            }
        })
        .catch(error => {
            console.error("Error deleting student:", error);
            alert("A network error occurred while deleting the student.");
        });
    }
}
function updateDashboard() {
    fetch('/get-dashboard-data')
        .then(response => response.json())
        .then(data => {
            document.getElementById('totalStudents').textContent = data.total_students;
            document.getElementById('presentToday').textContent = data.present_today;
            document.getElementById('absentToday').textContent = data.absent_today;
        })
        .catch(error => console.error('Error fetching dashboard data:', error));
}

// Call the function on page load
window.onload = updateDashboard;


// Example client-side password validation (optional)
document.addEventListener('DOMContentLoaded', function() {
    const resetPasswordForm = document.querySelector('form');
    if (resetPasswordForm) {
        resetPasswordForm.addEventListener('submit', function(event) {
            const newPassword = document.querySelector('input[name="new_password"]').value;
            if (newPassword.length < 8) {
                alert('Password must be at least 8 characters long.');
                event.preventDefault(); // Prevent form submission
            }
            // Add more password validation rules as needed
        });
    }
});

document.getElementById("reset-btn").addEventListener("click", function(event) {
    event.preventDefault(); // Prevent form from reloading page

    let email = document.getElementById("email").value; // Get email input

    if (!email) {
        alert("Please enter an email address!");
        return;
    }

    fetch("/send_reset_link", {
        method: "POST",
        headers: {
            "Content-Type": "application/json"
        },
        body: JSON.stringify({ email: email })
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            alert("Reset link sent successfully! Check your email.");
        } else {
            alert("Error: " + data.message);
        }
    })
    .catch(error => console.error("Error:", error));
});

document.getElementById("loginForm").addEventListener("submit", function(event) {
    let email = document.getElementById("email").value;
    let password = document.getElementById("password").value;

    if (!email || !password) {
        event.preventDefault(); // Stop form submission
        document.getElementById("EmailError").innerText = "Email is required!";
        document.getElementById("passwordError").innerText = "Password is required!";
    }
});
function markAttendance() {
    fetch('/mark_attendance', { method: 'POST' })
    .then(response => response.json())
    .then(data => alert(data.message))
    .catch(error => console.error('Error:', error));
}


// Function to populate the students table
function loadStudents() {
    fetch('/get-students')
        .then(response => response.json())
        .then(data => {
            const studentsList = document.getElementById('studentsList');
            studentsList.innerHTML = ''; // Clear existing rows

            data.students.forEach(student => {
                const row = `
                    <tr>
                        <td>${student.roll_no}</td>
                        <td>${student.name}</td>
                        <td>${student.class}</td>
                        <td>
                            <button class="btn btn-sm btn-warning" onclick="editStudent(${student.roll_no})">Edit</button>
                            <button class="btn btn-sm btn-danger" onclick="deleteStudent(${student.roll_no})">Delete</button>
                        </td>
                    </tr>
                `;
                studentsList.insertAdjacentHTML('beforeend', row);
            });
        })
        .catch(error => console.error('Error loading students:', error));
}

// Load students when the page loads
document.addEventListener('DOMContentLoaded', loadStudents);
// Function to populate the Edit Modal with student data
function editStudent(rollNo) {
    fetch(`/get-student/${rollNo}`)
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                // Populate the edit modal fields
                const editRollNoField = document.getElementById('editRollNo');
                editRollNoField.value = data.student.roll_no;
                editRollNoField.dataset.oldRollNo = data.student.roll_no; // Store original roll no
                document.getElementById('editStudentName').value = data.student.name;
                document.getElementById('editStudentClass').value = data.student.class;

                // Show the edit modal
                new bootstrap.Modal(document.getElementById('editStudentModal')).show();
            } else {
                alert(data.message);
            }
        })
        .catch(error => console.error('Error fetching student data:', error));
}
// Function to validate and update student details
function validateAndUpdateStudent() {
    // Clear previous errors
    document.getElementById("editRollNoError").textContent = "";
    document.getElementById("editStudentNameError").textContent = "";
    document.getElementById("editClassError").textContent = "";

    // Get input values
    const rollNo = document.getElementById('editRollNo').value.trim();
    const name = document.getElementById('editStudentName').value.trim();
    const className = document.getElementById('editStudentClass').value;

    let isValid = true;

    // Validate Roll No
    if (!rollNo || isNaN(rollNo)) {
        document.getElementById("editRollNoError").textContent = "Please enter a valid roll number.";
        isValid = false;
    }

    // Validate Name
    const nameRegex = /^[a-zA-Z\s]+$/;
    if (!name || !nameRegex.test(name)) {
        document.getElementById("editStudentNameError").textContent = "Please enter a valid name (only letters and spaces).";
        isValid = false;
    }

    // Validate Class Selection
    if (!className) {
        document.getElementById("editClassError").textContent = "Please select a class.";
        isValid = false;
    }

    // If all validations pass, update the student
    if (isValid) {
        updateStudent();
    }
}// Function to update student details
function updateStudentsList() {
    const tbody = document.getElementById('studentsList');
    tbody.innerHTML = '';

    fetch('/get_students')
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                students = data.students;

                if (students.length === 0) {
                    tbody.innerHTML = `<tr><td colspan="4" class="text-center">No students found</td></tr>`;
                    return;
                }

                students.forEach(student => {
                    const tr = document.createElement('tr');
                    tr.innerHTML = `
                        <td>${student.roll_no}</td>
                        <td>${student.name}</td>
                        <td>${student.class}</td>
                        <td>
                            <button class="btn btn-sm btn-warning" onclick="editStudent(${student.roll_no})">Edit</button>
                            <button class="btn btn-sm btn-danger" onclick="deleteStudent('${student.roll_no}')">
                                Delete
                            </button>
                        </td>
                    `;
                    tbody.appendChild(tr);
                });

                updateDashboard();
                updateAttendanceList(document.getElementById('classSelect').value);
            } else {
                console.error("Error fetching students:", data.status);
                alert("Error fetching students. Check the console.");
            }
        })
        .catch(error => {
            console.error("Network Error:", error);
            alert("A network error occurred.");
        });
}
function updateStudent() {
    const oldRollNo = document.getElementById('editRollNo').dataset.oldRollNo; // Get the original roll no
    const newRollNo = document.getElementById('editRollNo').value;
    const name = document.getElementById('editStudentName').value;
    const studentClass = document.getElementById('editStudentClass').value;
    const file = document.getElementById('editStudentFile').files[0];

    // Validate Roll No
    if (!newRollNo || isNaN(newRollNo)) {
        alert("Please enter a valid roll number.");
        return;
    }

    const formData = new FormData();
    formData.append('oldRollNo', oldRollNo); // Pass the original roll no
    formData.append('newRollNo', newRollNo); // Pass the new roll no
    formData.append('studentName', name);
    formData.append('studentClass', studentClass);
    if (file) formData.append('file', file);

    fetch('/update-student', {
        method: 'POST',
        body: formData,
    })
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                alert('Student updated successfully!');
                location.reload(); // Refresh the page to reflect changes
            } else {
                alert(data.message);
            }
        })
        .catch(error => console.error('Error updating student:', error));
}
