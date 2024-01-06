document.addEventListener('DOMContentLoaded', function() {
    let index = 0;
    const carouselContainer = document.querySelector('.carousel-container');
    const carouselSlide = document.getElementById('carousel');
    const slides = carouselSlide.getElementsByClassName('card');
    const slideWidth = slides[0].offsetWidth; // get the width of the card
    const slideMargin = 15; // Adjust this value if needed

    document.getElementById('carouselNext').addEventListener('click', () => {
        index = (index + 1) % slides.length;
        updateCarousel();
    });

    document.getElementById('carouselPrev').addEventListener('click', () => {
        index = (index - 1 + slides.length) % slides.length;
        updateCarousel();
    });

    function updateCarousel() {
        const newOffset = (slideWidth + slideMargin) * index;
        carouselSlide.style.transform = `translateX(-${newOffset}px)`;
    }
});