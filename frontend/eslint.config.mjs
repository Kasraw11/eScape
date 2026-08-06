import js from "@eslint/js";
import nextPlugin from "@next/eslint-plugin-next";

export default [
  {
    ignores: [".next/**", "dist/**", "out/**", "node_modules/**", "scripts/**"],
  },
  js.configs.recommended,
  {
    files: ["**/*.{js,jsx}"],
    plugins: {
      "@next/next": nextPlugin,
    },
    languageOptions: {
      ecmaVersion: "latest",
      sourceType: "module",
      parserOptions: {
        ecmaFeatures: {
          jsx: true,
        },
      },
      globals: {
        document: "readonly",
        expect: "readonly",
        fetch: "readonly",
        jest: "readonly",
        module: "readonly",
        process: "readonly",
        console: "readonly",
        window: "readonly",
      },
    },
    rules: {
      ...nextPlugin.configs["core-web-vitals"].rules,
      "no-unused-vars": "off",
    },
  },
  {
    files: ["**/*.test.{js,jsx}", "src/test/**/*.js"],
    languageOptions: {
      globals: {
        beforeEach: "readonly",
        describe: "readonly",
        it: "readonly",
      },
    },
  },
];
