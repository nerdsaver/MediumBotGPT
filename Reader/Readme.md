# Readme

1. ### **Medium Reader Bot Script**

   ```
   jsCopy codeconst puppeteer = require('puppeteer');
   
   async function autoScroll(page) {
       await page.evaluate(async () => {
           await new Promise((resolve) => {
               let totalHeight = 0;
               const distance = 100;
               const timer = setInterval(() => {
                   window.scrollBy(0, distance);
                   totalHeight += distance;
   
                   if (totalHeight >= document.body.scrollHeight) {
                       clearInterval(timer);
                       resolve();
                   }
               }, 300);
           });
       });
   }
   
   (async () => {
       const browser = await puppeteer.launch({ headless: false });
       const page = await browser.newPage();
       await page.setViewport({ width: 1280, height: 800 });
       await page.goto('https://medium.com/@nerdsaver/will-you-be-working-in-vr-lets-look-at-microsofts-volumetric-apps-95769403c43f', { waitUntil: 'networkidle2' });
       await autoScroll(page);
       await browser.close();
   })();
   ```

   ### **Steps to Run the Script**

   1. **Create and Navigate to the Project Directory:**

      ```
      shCopy codemkdir medium-reader
      cd medium-reader
      ```

   2. **Initialize a NodeJS Project:**

      ```
      sh
      Copy code
      npm init --yes
      ```

   3. **Install Puppeteer:**

      ```
      sh
      Copy code
      npm install puppeteer --save
      ```

   4. **Create `index.js` and Paste the Script:**

      - Create 

        ```
        index.js
        ```

        :

        ```
        sh
        Copy code
        touch index.js
        ```

      - Open `index.js` in your favorite code editor (e.g., VS Code) and paste the script above.

   5. **Run the Script:**

      ```
      sh
      Copy code
      node index.js
      ```

   This script will launch a Chromium browser in non-headless mode, navigate to the specified Medium article, and scroll to the bottom of the page. You will be able to see the entire process in action.

--------------------------------------------------------------------------------------------------------

### **Code Breakdown**

1. **Import Puppeteer:**

   ```
   js
   Copy code
   const puppeteer = require('puppeteer');
   ```

   - This line imports the Puppeteer library, which allows you to control a browser programmatically.

2. **Define `autoScroll` Function:**

   ```
   jsCopy codeasync function autoScroll(page) {
       await page.evaluate(async () => {
           await new Promise((resolve) => {
               let totalHeight = 0;
               const distance = 100;
               const timer = setInterval(() => {
                   window.scrollBy(0, distance);
                   totalHeight += distance;
   
                   if (totalHeight >= document.body.scrollHeight) {
                       clearInterval(timer);
                       resolve();
                   }
               }, 300);
           });
       });
   }
   ```

   - `autoScroll` Function Purpose:
     - This function scrolls the page in small increments to simulate human-like scrolling behavior.
   - `page.evaluate` Method:
     - This method runs JavaScript code within the context of the page.
   - Scrolling Logic:
     - The code creates a promise that resolves once the page is fully scrolled.
     - The `setInterval` function scrolls the page by 100 pixels every 300 milliseconds.
     - The `clearInterval` function stops the scrolling once the total height scrolled is equal to or greater than the page's scroll height.

3. **Main Async IIFE (Immediately Invoked Function Expression):**

   ```
   jsCopy code(async () => {
       const browser = await puppeteer.launch({ headless: false });
       const page = await browser.newPage();
       await page.setViewport({ width: 1280, height: 800 });
       await page.goto('https://medium.com/@nerdsaver/will-you-be-working-in-vr-lets-look-at-microsofts-volumetric-apps-95769403c43f', { waitUntil: 'networkidle2' });
       await autoScroll(page);
       await browser.close();
   })();
   ```

   - `(async () => { ... })();` Syntax:

     - This creates and immediately invokes an asynchronous function.

   - Launch Browser:

     ```
     js
     Copy code
     const browser = await puppeteer.launch({ headless: false });
     ```

     - Launches a new browser instance.
     - The `{ headless: false }` option opens the browser with a UI.

   - Open New Page:

     ```
     js
     Copy code
     const page = await browser.newPage();
     ```

     - Opens a new tab in the browser.

   - Set Viewport Size:

     ```
     js
     Copy code
     await page.setViewport({ width: 1280, height: 800 });
     ```

     - Sets the viewport size to 1280x800 pixels, which defines the visible area of the web page.

   - Navigate to Medium Article:

     ```
     js
     Copy code
     await page.goto('https://medium.com/@nerdsaver/will-you-be-working-in-vr-lets-look-at-microsofts-volumetric-apps-95769403c43f', { waitUntil: 'networkidle2' });
     ```

     - Opens the specified URL in the page.
     - The `{ waitUntil: 'networkidle2' }` option waits until there are no more than 2 network connections for at least 500ms, indicating that the page has fully loaded.

   - Scroll the Page:

     ```
     js
     Copy code
     await autoScroll(page);
     ```

     - Calls the `autoScroll` function to scroll down the entire page.

   - Close Browser:

     ```
     js
     Copy code
     await browser.close();
     ```

     - Closes the browser instance.

### **Summary:**

- The bot uses Puppeteer to automate browser actions.
- It launches a non-headless browser, opens a new page, sets the viewport size, and navigates to a specified Medium article.
- It scrolls down the entire page slowly, simulating human behavior.
- Finally, it closes the browser.

This script allows you to visually see the browser navigating to the Medium article and scrolling down the page.