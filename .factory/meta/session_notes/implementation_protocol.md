# Implementation Protocol (Mandatory)

Para cualquier nueva fase:

1. Nunca implementar directamente.
2. Primero:
   - Diseñar
   - Revisar diseño
   - Detectar conflictos con schemas/contracts
   - Ajustar

3. Implementación:
   - Prompt acotado
   - Archivos permitidos explícitos
   - Archivos prohibidos explícitos
   - No tocar runtime V1
   - No tocar agentes/comandos salvo fase específica

4. Post implementación:
   - Reportar:
     - archivos creados
     - tests ejecutados
     - resultado
     - riesgos

5. Git:
   - git status
   - git add selectivo
   - git diff --cached
   - verificar contaminación:
       framework-state.json
       .gitignore
       fba-agent-observer.ts
   - commit
   - verificar status

6. Nunca avanzar a siguiente fase sin revisar commit anterior.

7. Prioridad:
   simplicidad > automatización > agentes > runtime

8. Si una utility parece innecesaria:
   cuestionarla antes de implementarla.
