/**
 * Set-of-Marks (SoM) Page Annotation
 * Based on WebVoyager paper: https://arxiv.org/abs/2401.13919
 * 
 * This script:
 * 1. Finds all interactive elements on the page
 * 2. Adds numbered bounding boxes to each element
 * 3. Returns metadata about each element
 * 
 * Used by the agent to identify which elements to interact with.
 */

(function() {
  'use strict';

  // Global namespace to avoid conflicts
  window.__agent_marks__ = window.__agent_marks__ || {};

  /**
   * Remove all existing marks from the page
   */
  window.unmarkPage = function() {
    // Remove all marked elements
    const marks = document.querySelectorAll('[data-agent-mark="true"]');
    marks.forEach(mark => mark.remove());
    
    // Clear stored data
    window.__agent_marks__ = {};
  };

  /**
   * Mark all interactive elements on the page with numbered bounding boxes
   * @returns {Array} Array of bounding box metadata
   */
  window.markPage = function() {
    // First, clean up any existing marks
    window.unmarkPage();

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
      '[role="combobox"]',
      '[onclick]',
      '[contenteditable="true"]',
      'summary',
      '[tabindex]:not([tabindex="-1"])',
      '[data-testid]',
      '[aria-haspopup]',
      'div[class*="button"]',
      'div[class*="Button"]',
      'span[class*="button"]',
      'span[class*="Button"]'
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

      // Create label overlay (red box with number in top-left corner)
      const label = document.createElement('div');
      label.setAttribute('data-agent-mark', 'true');
      label.textContent = index;
      label.style.cssText = `
        position: fixed;
        left: ${rect.left}px;
        top: ${rect.top}px;
        background: #FF0000;
        color: #FFFFFF;
        padding: 2px 6px;
        font-size: 12px;
        font-weight: bold;
        font-family: monospace;
        border-radius: 3px;
        z-index: 2147483647;
        pointer-events: none;
        box-shadow: 0 2px 4px rgba(0,0,0,0.3);
      `;
      document.body.appendChild(label);

      // Create bounding box outline
      const box = document.createElement('div');
      box.setAttribute('data-agent-mark', 'true');
      box.style.cssText = `
        position: fixed;
        left: ${rect.left}px;
        top: ${rect.top}px;
        width: ${rect.width}px;
        height: ${rect.height}px;
        border: 2px solid #FF0000;
        z-index: 2147483646;
        pointer-events: none;
        box-sizing: border-box;
      `;
      document.body.appendChild(box);

      // Store bbox metadata
      bboxes.push({
        index: index,
        x: rect.left + rect.width / 2,   // Center X
        y: rect.top + rect.height / 2,    // Center Y
        width: rect.width,
        height: rect.height,
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

    // Store bboxes for reference
    window.__agent_marks__.bboxes = bboxes;

    return bboxes;
  };

  /**
   * Get bbox by index (helper function)
   * @param {number} index - The bbox index
   * @returns {Object} The bbox metadata
   */
  window.getBboxByIndex = function(index) {
    if (!window.__agent_marks__.bboxes) {
      return null;
    }
    return window.__agent_marks__.bboxes.find(bbox => bbox.index === index);
  };

  /**
   * Highlight a specific bbox (useful for debugging)
   * @param {number} index - The bbox index to highlight
   */
  window.highlightBbox = function(index) {
    const bbox = window.getBboxByIndex(index);
    if (!bbox) {
      console.error(`No bbox found with index ${index}`);
      return;
    }

    // Create highlight
    const highlight = document.createElement('div');
    highlight.setAttribute('data-agent-mark', 'true');
    highlight.style.cssText = `
      position: fixed;
      left: ${bbox.x - bbox.width/2}px;
      top: ${bbox.y - bbox.height/2}px;
      width: ${bbox.width}px;
      height: ${bbox.height}px;
      border: 4px solid #00FF00;
      background: rgba(0, 255, 0, 0.1);
      z-index: 2147483647;
      pointer-events: none;
      animation: pulse 1s infinite;
    `;
    
    // Add pulse animation
    const style = document.createElement('style');
    style.textContent = `
      @keyframes pulse {
        0%, 100% { opacity: 1; }
        50% { opacity: 0.5; }
      }
    `;
    document.head.appendChild(style);
    
    document.body.appendChild(highlight);
    
    console.log(`Highlighted bbox ${index}:`, bbox);
  };

  console.log('✅ Agent annotation script loaded');
  console.log('Usage:');
  console.log('  - markPage() - Add numbered boxes to interactive elements');
  console.log('  - unmarkPage() - Remove all marks');
  console.log('  - getBboxByIndex(n) - Get element info by number');
  console.log('  - highlightBbox(n) - Highlight specific element');

})();