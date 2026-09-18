// Set current year in footer
document.addEventListener('DOMContentLoaded', function() {
    const yearSpan = document.getElementById('current-year');
    if (yearSpan) {
        yearSpan.textContent = new Date().getFullYear();
    }
    
    // Show social links only if they have a real href (not TODO)
    const socialLinks = document.querySelectorAll('.footer-social-link[data-social]');
    socialLinks.forEach(link => {
        const href = link.getAttribute('href');
        if (href && !href.includes('TODO')) {
            link.style.display = 'flex';
        }
    });
});