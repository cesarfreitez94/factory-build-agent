#!/bin/bash
# =============================================================================
# fba-milestone-close.sh - Helper para cerrar un milestone del framework FBA
# =============================================================================
# Uso: ./scripts/fba-milestone-close.sh <M#> [base_branch]
#
# Ejemplo: ./scripts/fba-milestone-close.sh M12
#          ./scripts/fba-milestone-close.sh M11 milestone/11.0-foundation-hardening
#
# Este script es un helper para el usuario. Se ejecuta fuera de OpenCode.
# =============================================================================

set -e

MILESTONE="$1"
BASE_BRANCH="${2:-main}"

if [ -z "$MILESTONE" ]; then
    echo "Uso: $0 <M#> [base_branch]"
    echo ""
    echo "  M#             - Numero de milestone (ej: M12)"
    echo "  base_branch    - Branch base para el PR (default: main)"
    echo ""
    echo "Ejemplo: $0 M12"
    echo "         $0 M11 milestone/11.0-foundation-hardening"
    exit 1
fi

# Extraer numero de milestone (M12 -> 12)
MILESTONE_NUM="${MILESTONE#M}"
MILESTONE_BRANCH_PATTERN="milestone/${MILESTONE_NUM}.0-*"

echo "=== Cierre de Milestone ${MILESTONE} ==="
echo ""

# 1. Verificar estado del branch
echo "1. Verificando estado del branch..."
BRANCHES=$(git branch --list "$MILESTONE_BRANCH_PATTERN" 2>/dev/null || true)
if [ -z "$BRANCHES" ]; then
    echo "ERROR: No se encontro branch para ${MILESTONE}"
    exit 1
fi
echo "   Branch encontrado: $BRANCHES"
echo ""

# 2. Verificar ROADMAP.md
echo "2. Verificando ROADMAP.md..."
if grep -q "${MILESTONE}.*Completado" ROADMAP.md; then
    echo "   OK: milestone marcado como Completado"
else
    echo "   WARNING: milestone NO aparece como Completado en ROADMAP.md"
    echo "   Ejecutar: actualizar ROADMAP.md con fecha de fin"
fi
echo ""

# 3. Verificar CHANGELOG.md
echo "3. Verificando CHANGELOG.md..."
if grep -q "## ${MILESTONE}:" CHANGELOG.md || grep -q "${MILESTONE}" CHANGELOG.md; then
    echo "   OK: entrada de changelog encontrada"
else
    echo "   WARNING: NO se encontro entrada de ${MILESTONE} en CHANGELOG.md"
fi
echo ""

# 4. Verificar docs/testing/
echo "4. Verificando docs/testing/..."
TESTING_DOC="docs/testing/m${MILESTONE_NUM}-*.md"
if ls $TESTING_DOC 1> /dev/null 2>&1; then
    echo "   OK: documentacion de testing encontrada"
else
    echo "   WARNING: NO se encontro docs/testing/m${MILESTONE_NUM}-*.md"
fi
echo ""

# 5. Ejecutar tests
echo "5. Ejecutando tests..."
if pytest -q 2>/dev/null; then
    echo "   OK: tests pasan"
else
    echo "   ERROR: tests fallaron"
    exit 1
fi
echo ""

# 6. Resumen para PR
echo "=== Resumen para PR ==="
echo ""
echo "Branch: $(echo $BRANCHES | tr -d '[:space:]')"
echo "Base: ${BASE_BRANCH}"
echo ""
echo "Para abrir PR manualmente:"
echo "   gh pr create --base ${BASE_BRANCH} --head $(echo $BRANCHES | tr -d '[:space:]')"
echo ""
echo "Verificar antes de abrir PR:"
echo "   [ ] ROADMAP.md marca ${MILESTONE} como Completado con fecha"
echo "   [ ] CHANGELOG.md tiene entrada de cierre"
echo "   [ ] docs/testing/m${MILESTONE_NUM}-*.md existe"
echo "   [ ] Tests pasan (ya verificado arriba)"
echo "   [ ] Validacion manual del usuario completada"
echo ""

echo "=== Checklist Pre-PR ==="
echo ""
echo "Segun CONTRIBUTING.md, el PR de milestone debe incluir:"
echo "   - ROADMAP.md actualizado (milestone como Completado)"
echo "   - CHANGELOG.md con entrada de cierre del milestone"
echo "   - docs/testing/ con guia de testing"
echo ""
echo "El PR requiere validacion manual del usuario antes de abrir."
echo "El agente NO puede abrir PR a main sin confirmacion explicita."