// Test JavaScript file for canvas functionality
function testCanvas() {
    console.log('Canvas test function called');
    
    // This is a test file to verify canvas code viewing works
    const testElement = document.createElement('div');
    testElement.innerHTML = `
        <h2>Canvas Code Test</h2>
        <p>This JavaScript file should display properly in the canvas viewer.</p>
    `;
    
    return testElement;
}

// Test function with syntax highlighting
const canvasConfig = {
    theme: 'dark',
    language: 'javascript',
    features: [
        'syntax-highlighting',
        'line-numbers',
        'copy-button'
    ]
};

export { testCanvas, canvasConfig };
