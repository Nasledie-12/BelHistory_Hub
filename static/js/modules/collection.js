window.showCollectionNotification = function showCollectionNotification(message, isError = false) {
    const host = document.getElementById('app-notifications');
    if (!host) {
        window.alert(message);
        return;
    }

    host.innerHTML = '';
    const notice = document.createElement('div');
    notice.className = `pointer-events-auto max-w-xl rounded-2xl px-5 py-3 text-sm font-semibold shadow-lg ${isError ? 'bg-red-600 text-white' : 'bg-slate-900 text-white'}`;
    notice.textContent = message;
    host.appendChild(notice);

    window.setTimeout(() => {
        if (notice.parentElement === host) {
            notice.remove();
        }
    }, 3000);
};

window.addToCollection = function addToCollection(objectId) {
    fetch(`/add_to_collection/${objectId}`, {
        method: 'POST'
    })
        .then(response => response.json())
        .then(data => {
            window.showCollectionNotification(data.message, data.status === 'error');
        })
        .catch(error => {
            console.error('Error adding to collection:', error);
            window.showCollectionNotification('Не удалось добавить материал в коллекцию. Попробуйте ещё раз.', true);
        });
};

window.initCollectionInteractions = function initCollectionInteractions() {
    document.querySelectorAll('.add-to-collection-button').forEach(button => {
        button.addEventListener('click', () => {
            window.addToCollection(button.dataset.collectionObjectId);
        });
    });
};
