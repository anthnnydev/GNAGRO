// Dashboard JavaScript
// Funcionalidad para el menú de navegación y dropdowns

document.addEventListener('DOMContentLoaded', function() {
    
    // Toggle del menú móvil
    const mobileMenuButton = document.getElementById('mobile-menu-button');
    const mobileMenu = document.getElementById('mobile-menu');
    
    if (mobileMenuButton && mobileMenu) {
        mobileMenuButton.addEventListener('click', function() {
            mobileMenu.classList.toggle('hidden');
        });
    }

    // Toggle del menú de usuario
    const userMenuButton = document.getElementById('user-menu-button');
    const userMenuDropdown = document.getElementById('user-menu-dropdown');
    const userMenuChevron = document.getElementById('user-menu-chevron');
    const dropdownBackdrop = document.getElementById('dropdown-backdrop');
    
    if (userMenuButton) {
        userMenuButton.addEventListener('click', function(e) {
            e.preventDefault();
            e.stopPropagation();
            
            if (userMenuDropdown && userMenuChevron && dropdownBackdrop) {
                userMenuDropdown.classList.toggle('hidden');
                dropdownBackdrop.classList.toggle('hidden');
                userMenuChevron.classList.toggle('rotate-180');
            }
        });
    }

    // Función para cerrar el menú de usuario
    function closeUserMenu() {
        if (userMenuDropdown && userMenuChevron && dropdownBackdrop) {
            userMenuDropdown.classList.add('hidden');
            dropdownBackdrop.classList.add('hidden');
            userMenuChevron.classList.remove('rotate-180');
        }
    }

    // Cerrar menú de usuario cuando se hace click en el backdrop
    if (dropdownBackdrop) {
        dropdownBackdrop.addEventListener('click', function() {
            closeUserMenu();
        });
    }

    // Cerrar menús cuando se hace click fuera
    document.addEventListener('click', function(e) {
        const userMenu = document.getElementById('user-menu');
        
        // Cerrar menú de usuario si se hace click fuera
        if (userMenu && !userMenu.contains(e.target)) {
            closeUserMenu();
        }
        
        // Cerrar menú móvil si se hace click fuera
        if (mobileMenuButton && mobileMenu && 
            !mobileMenuButton.contains(e.target) && 
            !mobileMenu.contains(e.target)) {
            mobileMenu.classList.add('hidden');
        }
    });

    // Manejar tecla Escape para cerrar menús
    document.addEventListener('keydown', function(e) {
        if (e.key === 'Escape') {
            closeUserMenu();
            
            if (mobileMenu) {
                mobileMenu.classList.add('hidden');
            }
        }
    });

    // Añadir indicador visual de página activa
    function setActiveNavItem() {
        const currentPath = window.location.pathname;
        const navLinks = document.querySelectorAll('nav a, #mobile-menu a');
        
        navLinks.forEach(link => {
            const href = link.getAttribute('href');
            if (href && href !== '#' && currentPath.includes(href)) {
                link.classList.add('text-primary-600', 'bg-primary-50');
                link.classList.remove('text-gray-700');
            }
        });
    }

    // Activar indicador de navegación
    setActiveNavItem();

    // Efecto suave para las transiciones
    const elementsWithTransition = document.querySelectorAll('[class*="transition"]');
    elementsWithTransition.forEach(element => {
        element.style.transitionTimingFunction = 'cubic-bezier(0.4, 0, 0.2, 1)';
    });

    // Funcionalidad adicional para notificaciones (si existe el botón)
    const notificationButton = document.querySelector('.fa-bell').closest('button');
    if (notificationButton) {
        notificationButton.addEventListener('click', function() {
            // Aquí puedes agregar la lógica para mostrar notificaciones
            console.log('Mostrar notificaciones');
        });
    }

    // Mejorar accesibilidad con focus
    document.addEventListener('keydown', function(e) {
        if (e.key === 'Tab') {
            // Asegurar que el foco sea visible
            const focusedElement = document.activeElement;
            if (focusedElement) {
                focusedElement.classList.add('focus-visible');
            }
        }
    });

    // Limpiar clases de focus cuando no se use teclado
    document.addEventListener('mousedown', function() {
        const focusedElements = document.querySelectorAll('.focus-visible');
        focusedElements.forEach(element => {
            element.classList.remove('focus-visible');
        });
    });
});