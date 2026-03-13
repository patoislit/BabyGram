// lazy-loading.js

// Function to dynamically load images based on connection quality
function lazyLoadImages() {
    const images = document.querySelectorAll('img[data-src]');
    const config = {
        root: null, // Use the viewport as the container
        rootMargin: '0px',
        threshold: 0.1 // Load image when 10% in viewport
    };

    const imageObserver = new IntersectionObserver((entries, observer) => {
        entries.forEach(entry => {
            if (entry.isIntersecting) {
                const img = entry.target;
                img.src = img.dataset.src; // Change to actual source
                img.onload = () => {
                    img.classList.add('loaded');
                    observer.unobserve(img);
                };
            }
        });
    }, config);

    images.forEach(image => {
        imageObserver.observe(image);
    });
}

// Call lazyLoadImages when DOM content is loaded
document.addEventListener('DOMContentLoaded', lazyLoadImages);