document.addEventListener('DOMContentLoaded', () => {
    if (typeof window.initQuizInteractions === 'function') {
        window.initQuizInteractions();
    }

    if (typeof window.initCollectionInteractions === 'function') {
        window.initCollectionInteractions();
    }

    if (typeof window.initHeroSlider === 'function') {
        window.initHeroSlider();
    }

    if (typeof window.initImageViewer === 'function') {
        window.initImageViewer();
    }

    if (typeof window.initMobileNavigation === 'function') {
        window.initMobileNavigation();
    }
});
