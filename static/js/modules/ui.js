window.initHeroSlider = function initHeroSlider() {
    const slider = document.querySelector('.heroes-slider');
    const leftBtn = document.querySelector('.heroes-slider-prev');
    const rightBtn = document.querySelector('.heroes-slider-next');

    if (!slider || !leftBtn || !rightBtn) {
        return;
    }

    leftBtn.addEventListener('click', () => {
        slider.scrollBy({ left: -320, behavior: 'smooth' });
    });

    rightBtn.addEventListener('click', () => {
        slider.scrollBy({ left: 320, behavior: 'smooth' });
    });
};

window.initImageViewer = function initImageViewer() {
    const galleryImages = document.querySelectorAll('.aspect-video img, .rounded-3xl img');

    galleryImages.forEach(img => {
        img.style.cursor = 'zoom-in';
        img.addEventListener('click', () => {
            const overlay = document.createElement('div');
            overlay.className = 'fixed inset-0 bg-black/90 z-[100] flex items-center justify-center p-4 cursor-zoom-out';
            overlay.setAttribute('role', 'dialog');
            overlay.setAttribute('aria-modal', 'true');

            const fullImg = document.createElement('img');
            fullImg.src = img.src;
            fullImg.alt = img.alt || 'Увеличенное изображение';
            fullImg.className = 'max-w-full max-h-full object-contain rounded-lg shadow-2xl';

            const closeButton = document.createElement('button');
            closeButton.type = 'button';
            closeButton.className = 'absolute top-4 right-4 inline-flex h-11 w-11 items-center justify-center rounded-full bg-white/10 text-white transition hover:bg-white/20';
            closeButton.setAttribute('aria-label', 'Закрыть просмотр изображения');
            closeButton.innerHTML = '<i class="fas fa-xmark text-xl" aria-hidden="true"></i>';

            const closeOverlay = () => {
                document.body.style.overflow = '';
                document.removeEventListener('keydown', onEscapePress);
                overlay.remove();
            };

            const onEscapePress = event => {
                if (event.key === 'Escape') {
                    closeOverlay();
                }
            };

            document.body.style.overflow = 'hidden';
            document.addEventListener('keydown', onEscapePress);
            overlay.appendChild(fullImg);
            overlay.appendChild(closeButton);
            document.body.appendChild(overlay);

            closeButton.addEventListener('click', event => {
                event.stopPropagation();
                closeOverlay();
            });
            overlay.addEventListener('click', closeOverlay);
        });
    });
};

window.initMobileNavigation = function initMobileNavigation() {
    const toggleButton = document.querySelector('[data-mobile-nav-toggle]');
    const navigation = document.getElementById('mobile-navigation');
    const navigationIcon = document.querySelector('[data-mobile-nav-icon]');

    if (!toggleButton || !navigation) {
        return;
    }

    const setNavigationState = isOpen => {
        navigation.classList.toggle('hidden', !isOpen);
        toggleButton.setAttribute('aria-expanded', String(isOpen));
        toggleButton.setAttribute('aria-label', isOpen ? 'Закрыть мобильное меню' : 'Открыть мобильное меню');
        navigation.setAttribute('aria-hidden', String(!isOpen));

        if (navigationIcon) {
            navigationIcon.classList.toggle('fa-bars', !isOpen);
            navigationIcon.classList.toggle('fa-xmark', isOpen);
        }

        const label = toggleButton.querySelector('[data-mobile-nav-label]');
        if (label) {
            label.textContent = isOpen ? 'Закрыть мобильное меню' : 'Открыть мобильное меню';
        }
    };

    toggleButton.addEventListener('click', () => {
        const isOpen = navigation.classList.contains('hidden');
        setNavigationState(isOpen);
    });

    navigation.querySelectorAll('a').forEach(link => {
        link.addEventListener('click', () => {
            setNavigationState(false);
        });
    });

    document.addEventListener('keydown', event => {
        if (event.key === 'Escape') {
            setNavigationState(false);
        }
    });
};
