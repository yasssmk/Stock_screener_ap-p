import fs from 'fs'
import path from 'path';


function functionsErrorLog(functionName, errorMessage, logName, symbol = '') {
    const errorTime = new Date().toISOString();
    
    const errorData = `"${errorTime}","${functionName}","${symbol}","${errorMessage}"\n`;

    const errorLogDir = path.join(__dirname, 'errors_logs');
    const errorLogPath = path.join(errorLogDir, logName);

    // Ensure the directory exists
    if (!fs.existsSync(errorLogDir)) {
        fs.mkdirSync(errorLogDir);
    }

    // Check if the file exists to add header
    if (!fs.existsSync(errorLogPath)) {
        fs.writeFileSync(errorLogPath, "Time,Function,Symbol,Error\n");
    }

    // Append the new error to the file
    fs.appendFileSync(errorLogPath, errorData);
}

// Usage example
functionsErrorLog('testFunction', 'Something went wrong', 'Node_requests.csv', 'TEST');
