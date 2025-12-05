document.addEventListener('DOMContentLoaded', function() {
    const shareModal = document.getElementById('shareModal');
    const searchInput = document.getElementById('userSearchInput');
    const searchResults = document.getElementById('searchResults');
    const selectedUsersList = document.getElementById('selectedUsersList');
    const shareForm = document.getElementById('shareForm');
    const sharePrivateRadio = document.getElementById('sharePrivate');
    const sharePublicRadio = document.getElementById('sharePublic');
    const privateShareSection = document.getElementById('privateShareSection');
    
    let selectedUsers = new Set();

    // Handle Modal Open
    shareModal.addEventListener('show.bs.modal', function(event) {
        const button = event.relatedTarget;
        const fileId = button.getAttribute('data-file-id');
        const fileName = button.getAttribute('data-file-name');
        
        const modalTitle = shareModal.querySelector('.modal-title');
        modalTitle.textContent = 'Share File: ' + fileName;
        
        // Update form action
        shareForm.action = '/share/' + fileId;
        
        // Reset state
        searchInput.value = '';
        searchResults.innerHTML = '';
        selectedUsers.clear();
        updateSelectedUsersDisplay();
        sharePrivateRadio.checked = true;
        togglePrivateSection();
    });

    // Handle Share Type Toggle
    sharePrivateRadio.addEventListener('change', togglePrivateSection);
    sharePublicRadio.addEventListener('change', togglePrivateSection);

    function togglePrivateSection() {
        if (sharePublicRadio.checked) {
            privateShareSection.classList.add('d-none');
        } else {
            privateShareSection.classList.remove('d-none');
        }
    }

    // Handle Search
    let debounceTimer;
    searchInput.addEventListener('input', function() {
        clearTimeout(debounceTimer);
        const query = this.value.trim();
        
        if (query.length < 1) {
            searchResults.innerHTML = '';
            return;
        }

        debounceTimer = setTimeout(() => {
            fetch(`/api/search_users?q=${encodeURIComponent(query)}`)
                .then(response => response.json())
                .then(users => {
                    searchResults.innerHTML = '';
                    if (users.length === 0) {
                        searchResults.innerHTML = '<div class="list-group-item text-muted">No users found</div>';
                        return;
                    }
                    
                    users.forEach(user => {
                        const item = document.createElement('a');
                        item.href = '#';
                        item.className = 'list-group-item list-group-item-action';
                        item.textContent = user.username;
                        item.onclick = function(e) {
                            e.preventDefault();
                            addUser(user.username);
                        };
                        searchResults.appendChild(item);
                    });
                });
        }, 300);
    });

    function addUser(username) {
        if (!selectedUsers.has(username)) {
            selectedUsers.add(username);
            updateSelectedUsersDisplay();
        }
        searchInput.value = '';
        searchResults.innerHTML = '';
    }

    function removeUser(username) {
        selectedUsers.delete(username);
        updateSelectedUsersDisplay();
    }

    function updateSelectedUsersDisplay() {
        selectedUsersList.innerHTML = '';
        selectedUsers.forEach(username => {
            const badge = document.createElement('div');
            badge.className = 'badge bg-primary d-flex align-items-center p-2';
            badge.innerHTML = `
                <span class="me-2">${username}</span>
                <button type="button" class="btn-close btn-close-white small" aria-label="Remove"></button>
                <input type="hidden" name="usernames[]" value="${username}">
            `;
            badge.querySelector('.btn-close').onclick = () => removeUser(username);
            selectedUsersList.appendChild(badge);
        });
    }
});
