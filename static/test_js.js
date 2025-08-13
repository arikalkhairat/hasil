// Test JavaScript structure from HTML
console.log("Testing tab functionality");

function testTabs() {
    const tabBtns = document.querySelectorAll('.tab-btn');
    const tabPanes = document.querySelectorAll('.tab-pane');
    
    console.log('Found', tabBtns.length, 'tab buttons');
    console.log('Found', tabPanes.length, 'tab panes');
    
    tabBtns.forEach((btn, index) => {
        console.log(`Button ${index}:`, btn.getAttribute('data-tab'));
    });
    
    tabPanes.forEach((pane, index) => {
        console.log(`Pane ${index}:`, pane.id);
    });
}

// Test when DOM is ready
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', testTabs);
} else {
    testTabs();
}
