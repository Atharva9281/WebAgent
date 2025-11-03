/**
 * Clean Set-of-Marks (SoM) Page Annotation
 * Version 2.0 - NO DOM MANIPULATION
 * 
 * This script ONLY returns element data without adding any visual elements.
 * Boxes are added to screenshots using Python PIL instead of DOM manipulation.
 * 
 * Benefits:
 * - User sees clean page throughout automation
 * - No visual interference with page interaction
 * - Better for production use
 * - Eliminates timing issues with DOM rendering
 */

(function() {
  'use strict';

  // Global namespace to avoid conflicts
  window.__agent_marks_clean__ = window.__agent_marks_clean__ || {};

  /**
   * Get all interactive elements and their bounding boxes
   * WITHOUT rendering any visual elements to the DOM
   * @returns {Array} Array of bounding box metadata
   */
  window.getInteractiveElements = function() {
    // CSS selectors for interactive elements
    const interactiveSelectors = [
      'a[href]',
      'button',
      'input:not([type="hidden"])',
      'textarea',
      'select',
      '[role="button"]',
      '[role="link"]',
      '[role="tab"]',
      '[role="menuitem"]',
      '[role="option"]',
      '[role="checkbox"]',
      '[role="radio"]',
      '[role="textbox"]',
      '[onclick]',
      '[contenteditable="true"]',
      'summary',
      '[tabindex]:not([tabindex="-1"])'
    ];

    // Find all interactive elements
    const selector = interactiveSelectors.join(', ');
    const allElements = Array.from(document.querySelectorAll(selector));
    
    // Remove duplicates (element might match multiple selectors)
    const uniqueElements = Array.from(new Set(allElements));

    const bboxes = [];
    let index = 0;

    uniqueElements.forEach(element => {
      // Get bounding rectangle
      const rect = element.getBoundingClientRect();
      
      // Skip if element is not visible or too small
      if (rect.width < 5 || rect.height < 5) {
        return;
      }

      if (rect.top < -100 || rect.left < -100) {
        return;
      }

      // Check if element is actually visible
      const style = window.getComputedStyle(element);
      if (style.display === 'none' || 
          style.visibility === 'hidden' || 
          style.opacity === '0') {
        return;
      }

      // Get element text content
      let text = '';
      if (element.tagName === 'INPUT' || element.tagName === 'TEXTAREA') {
        text = element.value || element.placeholder || '';
      } else {
        // Get direct text content (not from children)
        text = element.innerText || element.textContent || '';
      }
      
      // Limit text length
      text = text.trim().substring(0, 100);

      // Get ARIA label for better element description
      const ariaLabel = element.getAttribute('aria-label') || 
                       element.getAttribute('title') || 
                       element.getAttribute('alt') || '';

      // Store bbox metadata (NO DOM MANIPULATION - PURE DATA)
      bboxes.push({
        index: index,
        x: Math.round(rect.left),
        y: Math.round(rect.top),
        width: Math.round(rect.width),
        height: Math.round(rect.height),
        centerX: Math.round(rect.left + rect.width / 2),   // Center X for clicking
        centerY: Math.round(rect.top + rect.height / 2),    // Center Y for clicking
        text: text,
        type: element.tagName.toLowerCase(),
        ariaLabel: ariaLabel,
        role: element.getAttribute('role') || '',
        href: element.href || '',
        id: element.id || '',
        className: element.className || ''
      });

      index++;
    });

    // Store bboxes for reference (no DOM elements stored)
    window.__agent_marks_clean__.bboxes = bboxes;

    return bboxes;
  };

  /**
   * Get bbox by index (helper function)
   * @param {number} index - The bbox index
   * @returns {Object} The bbox metadata
   */
  window.getBboxByIndexClean = function(index) {
    if (!window.__agent_marks_clean__.bboxes) {
      return null;
    }
    return window.__agent_marks_clean__.bboxes.find(bbox => bbox.index === index);
  };

  /**
   * Clear stored data
   */
  window.clearInteractiveElements = function() {
    window.__agent_marks_clean__ = {};
  };

  // Legacy compatibility - redirect to new functions
  window.markPageClean = window.getInteractiveElements;
  window.unmarkPageClean = window.clearInteractiveElements;

  console.log('✅ Clean agent annotation script loaded');
  console.log('Usage:');
  console.log('  - getInteractiveElements() - Get element data (NO VISUAL RENDERING)');
  console.log('  - getBboxByIndexClean(n) - Get element info by number');
  console.log('  - clearInteractiveElements() - Clear stored data');
  console.log('  - markPageClean() - Alias for getInteractiveElements()');
  console.log('');
  console.log('📸 Image annotation will be handled by Python PIL');
  console.log('👀 User sees clean page throughout automation');

})();