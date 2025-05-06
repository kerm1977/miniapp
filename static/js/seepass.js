function togglePasswordVisibility(inputId, checkboxId) {
    const passwordInput = document.getElementById(inputId);
    const showPasswordCheckbox = document.getElementById(checkboxId);
    if (showPasswordCheckbox.checked) {
        passwordInput.type = "text";
    } else {
        passwordInput.type = "password";
    }
}
