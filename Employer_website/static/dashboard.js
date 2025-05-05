document.addEventListener('DOMContentLoaded', function () {
    const uploadBtn = document.getElementById('uploadDocBtn');
    const uploadOverlay = document.getElementById('uploadOverlay');
    const closeUpload = document.getElementById('closeUpload');
    const uploadForm = document.getElementById('uploadForm');
    const pdfFile = document.getElementById('pdfFile');

    // Open upload dialog
    uploadBtn.addEventListener('click', () => {
        uploadOverlay.style.display = 'flex';
    });

    // Close upload dialog
    closeUpload.addEventListener('click', () => {
        uploadOverlay.style.display = 'none';
        uploadForm.reset();
    });

    // Close dialog by clicking outside the box
    window.addEventListener('click', (e) => {
        if (e.target === uploadOverlay) {
            uploadOverlay.style.display = 'none';
            uploadForm.reset();
        }
    });

    // Handle form submission
uploadForm.addEventListener('submit', () => {
    // Optionally: you can still show an alert before it goes:
    alert('Uploading your PDF...');
});

});


document.addEventListener('DOMContentLoaded', () => {
    const enterRolesBtn = document.getElementById('enterRolesBtn');
    const rolesOverlay = document.getElementById('rolesOverlay');
    const closeRoles = document.getElementById('closeRoles');
    const rolesForm = document.getElementById('rolesForm');
    const rolesInput = document.getElementById('rolesInput');

    enterRolesBtn.addEventListener('click', () => {
        rolesOverlay.style.display = 'flex';
    });

    closeRoles.addEventListener('click', () => {
        rolesOverlay.style.display = 'none';
        rolesForm.reset();
    });

    window.addEventListener('click', (e) => {
        if (e.target === rolesOverlay) {
            rolesOverlay.style.display = 'none';
            rolesForm.reset();
        }
    });

    rolesForm.addEventListener('submit', (e) => {
        e.preventDefault();
        const rolesEntered = rolesInput.value.split(',')
            .map(role => role.trim())
            .filter(role => role !== '');

        if (rolesEntered.length > 0) {
            fetch('/create_roles_table', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({ roles: rolesEntered, organization: 'School' })  // You can dynamically set the organization
            })
            .then(response => response.json())
            .then(data => {
                alert(data.message);
                rolesOverlay.style.display = 'none';
                rolesForm.reset();
            })
            .catch(error => {
                console.error('Error:', error);
                alert('Failed to create table');
            });
        } else {
            alert('Please enter at least one valid role.');
        }
    });
});
