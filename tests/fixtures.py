SAMPLE_DIFF = """diff --git a/src/app.py b/src/app.py
index 1234567..abcdefg 100644
--- a/src/app.py
+++ b/src/app.py
@@ -10,3 +10,5 @@ def hello():
     print("hello")
+    password = "hardcoded-secret"
+    eval(user_input)
     return True
diff --git a/yarn.lock b/yarn.lock
index 1111111..2222222 100644
--- a/yarn.lock
+++ b/yarn.lock
@@ -1,3 +1,4 @@
 # yarn lockfile v1
+updated 1.0.0
diff --git a/src/utils.ts b/src/utils.ts
index aaa..bbb 100644
--- a/src/utils.ts
+++ b/src/utils.ts
@@ -1,4 +1,6 @@
 export function add(a: number, b: number) {
+  if (a == null) return 0;
   return a + b;
 }
"""
