# Shree Mobile – React Native Frontend Roadmap  

Target developer profile: beginner to intermediate developer working primarily with AI coding assistants

## Core Functional Objectives

- Conversational chat interface with AI financial analyst (Gemini-powered backend)  
- Display backend responses formatted in Markdown  
- Render structured data visualizations (candlestick, line, bar, forecast bands) when backend returns a `data` block  
- Support file upload (PDF, Excel primarily) to provide document context to the AI  
- Allow users to manually add text context (notes, articles, personal observations)  
- Simple, persistent authentication using JWT stored securely on device  

## Design & Architecture Constraints

- State management: React Context + useState / useReducer only  
- No TypeScript in initial implementation  
- Styling: NativeWind (Tailwind CSS for React Native) with full dark mode support  
- Avoid complex custom navigation patterns  

## Recommended Technology Stack (March 2026 – NativeWind edition)

| Purpose                  | Library / Decision                               | Rationale / Notes                                                                 |
|--------------------------|--------------------------------------------------|-----------------------------------------------------------------------------------|
| Navigation               | @react-navigation/native + @react-navigation/native-stack | Most documented navigation solution                                               |
| Styling                  | nativewind                                       | Tailwind CSS syntax in React Native, built-in dark mode support                   |
| UI Components            | react-native-paper (minimal usage)               | Use only for modals/buttons when needed — rest via NativeWind                     |
| HTTP Client              | axios                                            | Reliable interceptors and error handling                                          |
| Charts                   | react-native-svg + react-native-svg-charts       | Vector-based charts suitable for candlestick, forecast bands                      |
| File / Document Picker   | react-native-document-picker                     | Reliable cross-platform document selection                                        |
| Secure Storage           | @react-native-async-storage/async-storage        | Standard choice for JWT storage                                                   |
| Markdown Rendering       | react-native-markdown-display                    | Acceptable rendering quality for assistant replies                                |
| Icons                    | react-native-vector-icons (MaterialCommunityIcons) | Broad free icon coverage                                                        |

## Folder Structure (recommended layout with NativeWind)

```
shree-mobile/
├── src/
│   ├── assets/
│   │   ├── images/
│   │   └── fonts/
│   │
│   ├── components/
│   │   ├── common/
│   │   │   ├── Button.jsx
│   │   │   ├── Card.jsx
│   │   │   ├── LoadingIndicator.jsx
│   │   │   └── ErrorMessage.jsx
│   │   ├── chat/
│   │   │   ├── ChatMessage.jsx
│   │   │   ├── ChartRenderer.jsx
│   │   │   └── InputArea.jsx
│   │   └── session/
│   │       ├── UploadedFileChip.jsx
│   │       └── ContextInputModal.jsx
│   │
│   ├── contexts/
│   │   ├── AuthContext.jsx
│   │   └── ThemeContext.jsx           # light/dark mode state & toggle
│   │
│   ├── navigation/
│   │   ├── RootNavigator.jsx
│   │   └── screenNames.js
│   │
│   ├── screens/
│   │   ├── LoginScreen.jsx
│   │   ├── HomeScreen.jsx
│   │   ├── ChatScreen.jsx
│   │   ├── ContextInputScreen.jsx     # or modal
│   │   └── SettingsScreen.jsx         # includes theme toggle
│   │
│   ├── services/
│   │   ├── api.js
│   │   ├── authService.js
│   │   └── sessionService.js
│   │
│   ├── utils/
│   │   ├── formatters.js
│   │   ├── constants.js
│   │   └── helpers.js
│   │
│   └── App.jsx
│
├── .env
├── .env.example
├── babel.config.js
├── metro.config.js
├── tailwind.config.js                 # NativeWind configuration
├── package.json
└── README.md
```

## Development Roadmap – 5 Milestones

### Milestone 0 – Project Skeleton & NativeWind Setup (3–5 days)

- Initialize project: `npx react-native init shree-mobile --version 0.75`  
- Install NativeWind and all dependencies (exact commands below)  
- Create folder structure  
- Set up `.env` + tailwind.config.js + babel.config.js  
- Create minimal `App.jsx` with ThemeProvider  
- Commit to repository  

### Milestone 1 – Authentication & Navigation (4–8 days)

- Implement `AuthContext` + token persistence  
- Build `LoginScreen` with NativeWind classes (`className="..."`)  
- Set up protected navigation with conditional stack  
- Apply consistent dark/light styling via `className`  

### Milestone 2 – Core Chat Experience (text only) (6–11 days)

- Implement `ChatScreen` using `FlatList` (inverted)  
- Create `ChatMessage` with Markdown + NativeWind styling  
- Build input area with proper keyboard handling  
- Support automatic theme switching in message bubbles  

### Milestone 3 – File Upload & Text Context (5–8 days)

- Document picker + upload flow with progress feedback  
- Display uploaded files with NativeWind-styled chips  
- Context input modal/screen with dark mode support  

### Milestone 4 – Data Visualization (Charts) (8–13 days)

- Implement `ChartRenderer` component  
- Use NativeWind for chart container styling  
- Ensure chart colors adapt to current theme (light/dark)  
- Support candlestick, line, bar, forecast band  

### Milestone 5 – Polish & Theme Features (5–10 days)

- Add theme toggle in Settings screen  
- Implement system theme detection (Appearance API)  
- Consistent loading/error states with theme support  
- Final UI polish and small UX improvements  

## Project Setup – Detailed Step-by-Step Guide (NativeWind + Dark Theme)

### 1. Create the project

```bash
npx react-native init shree-mobile --version 0.75
cd shree-mobile
```

### 2. Install all required dependencies

```bash
# NativeWind + Tailwind
npm install nativewind
npm install --save-dev tailwindcss@3.4.1

# Required by NativeWind
npx expo install react-native-reanimated react-native-safe-area-context react-native-screens

# Navigation
npm install @react-navigation/native @react-navigation/native-stack

# Other libraries
npm install axios @react-native-async-storage/async-storage
npm install react-native-svg react-native-svg-charts
npm install react-native-document-picker
npm install react-native-markdown-display
npm install react-native-vector-icons
npm install react-native-dotenv
```

### 3. Create `tailwind.config.js` (root folder)

```js
/** @type {import('tailwindcss').Config} */
module.exports = {
  content: [
    "./App.{js,jsx,ts,tsx}",
    "./src/**/*.{js,jsx,ts,tsx}",
  ],
  presets: [require("nativewind/preset")],
  theme: {
    extend: {
      colors: {
        primary: {
          DEFAULT: '#00695C',
          dark: '#004D40',
        },
        accent: '#FF5722',
        background: {
          light: '#F5F5F5',
          dark: '#111827',
        },
        surface: {
          light: '#FFFFFF',
          dark: '#1F2937',
        },
        text: {
          light: '#212121',
          dark: '#F3F4F6',
        },
        textSecondary: {
          light: '#757575',
          dark: '#9CA3AF',
        },
      },
    },
  },
  plugins: [],
  darkMode: 'class',
};
```

### 4. Replace entire `babel.config.js` with this exact content

```js
module.exports = function (api) {
  api.cache(true);

  return {
    presets: ['module:metro-react-native-babel-preset'],

    plugins: [
      // NativeWind MUST come first
      'nativewind/babel',

      // react-native-dotenv for .env support
      [
        'module:react-native-dotenv',
        {
          moduleName: '@env',
          path: '.env',
          safe: false,
          allowUndefined: true,
        },
      ],
    ],
  };
};
```

### 5. Create `src/contexts/ThemeContext.jsx` (exact file)

```jsx
import { createContext, useContext, useState, useEffect } from 'react';
import { Appearance } from 'react-native';

const ThemeContext = createContext();

export function ThemeProvider({ children }) {
  const [theme, setTheme] = useState(Appearance.getColorScheme() || 'light');

  useEffect(() => {
    const subscription = Appearance.addChangeListener(({ colorScheme }) => {
      setTheme(colorScheme || 'light');
    });
    return () => subscription.remove();
  }, []);

  const toggleTheme = () => {
    setTheme(prev => (prev === 'light' ? 'dark' : 'light'));
  };

  return (
    <ThemeContext.Provider value={{ theme, toggleTheme }}>
      {children}
    </ThemeContext.Provider>
  );
}

export const useTheme = () => useContext(ThemeContext);
```

### 6. Update `src/App.jsx` (exact minimal version)

```jsx
import { ThemeProvider } from './src/contexts/ThemeContext';
import RootNavigator from './src/navigation/RootNavigator';

export default function App() {
  return (
    <ThemeProvider>
      <RootNavigator />
    </ThemeProvider>
  );
}
```

### 7. Create `.env.example` and `.env`

**.env.example**
```
API_URL=http://192.168.1.xxx:8000
```

**.env** (your real backend URL – never commit)
```
API_URL=http://192.168.1.xxx:8000
```

### 8. How to use in any component (example)

```jsx
import { useTheme } from '../contexts/ThemeContext';
import { API_URL } from '@env';

export default function ExampleScreen() {
  const { theme } = useTheme();

  return (
    <View className="flex-1 bg-background-light dark:bg-background-dark p-4">
      <Text className="text-text-light dark:text-text-dark text-xl">
        Hello Shree
      </Text>
    </View>
  );
}
```

### 9. Final step after all files are created

```bash
npx react-native start --reset-cache
```

Then run the app:

```bash
npx react-native run-android
# or
npx react-native run-ios
```
