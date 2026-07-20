// Inicialización de Mermaid para renderizar diagramas en páginas
(function() {
  'use strict';

  // Función para inicializar Mermaid
  function initMermaid() {
    // Verificar que Mermaid esté disponible
    if (typeof mermaid === 'undefined') {
      console.warn('Mermaid no está disponible');
      return;
    }

    // Configuración de Mermaid
    mermaid.initialize({
      startOnLoad: false,
      securityLevel: 'loose',
      theme: 'default',
      flowchart: {
        useMaxWidth: true,
        htmlLabels: true
      },
      sequence: {
        useMaxWidth: true
      }
    });

    // Función para renderizar un diagrama
    function renderDiagram(element) {
      if (element.classList.contains('mermaid-rendered')) {
        return;
      }

      element.classList.add('mermaid-rendered');

      try {
        // Obtener el contenido del diagrama
        const diagramText = element.textContent || element.innerText;
        
        if (!diagramText || diagramText.trim() === '') {
          console.warn('Diagrama vacío encontrado');
          return;
        }

        // Renderizar el diagrama
        mermaid.render('mermaid-' + Math.random().toString(36).substr(2, 9), diagramText, function(svgCode) {
          element.innerHTML = svgCode;
        });

      } catch (error) {
        console.error('Error renderizando diagrama Mermaid:', error);
        element.innerHTML = '<div style="color: red; padding: 1rem; border: 1px solid red; border-radius: 0.5rem; background-color: #fff3f3;">Error al renderizar el diagrama Mermaid. Verifica la sintaxis.</div>';
      }
    }

    // Función para procesar todos los diagramas
    function processDiagrams() {
      const mermaidElements = document.querySelectorAll('pre code.language-mermaid, .mermaid');
      
      mermaidElements.forEach(function(element) {
        // Si es un elemento pre code, usar el elemento padre
        const targetElement = element.tagName === 'CODE' ? element.parentElement : element;
        renderDiagram(targetElement);
      });
    }

    // Procesar diagramas existentes
    processDiagrams();

    // Observar cambios en el DOM para nuevos diagramas
    if (typeof MutationObserver !== 'undefined') {
      const observer = new MutationObserver(function(mutations) {
        let shouldProcess = false;
        
        mutations.forEach(function(mutation) {
          if (mutation.type === 'childList') {
            mutation.addedNodes.forEach(function(node) {
              if (node.nodeType === Node.ELEMENT_NODE) {
                if (node.classList && (node.classList.contains('mermaid') || node.querySelector('.mermaid'))) {
                  shouldProcess = true;
                }
              }
            });
          }
        });

        if (shouldProcess) {
          setTimeout(processDiagrams, 100);
        }
      });

      observer.observe(document.body, {
        childList: true,
        subtree: true
      });
    }
  }

  // Función para esperar a que Mermaid se cargue
  function waitForMermaid() {
    if (typeof mermaid !== 'undefined') {
      initMermaid();
    } else {
      setTimeout(waitForMermaid, 100);
    }
  }

  // Inicializar cuando el DOM esté listo
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', waitForMermaid);
  } else {
    waitForMermaid();
  }

  // También inicializar cuando la ventana se cargue completamente
  window.addEventListener('load', function() {
    setTimeout(waitForMermaid, 100);
  });

})();
