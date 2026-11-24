# Contribución Carlos — F22 seed 14

Paquete reproducible del candidato seleccionado para la entrega. Permite que el
equipo descargue los pesos verificados y ejecute la cascada sin utilizar los
notebooks ni las carpetas de simulación.

## Componentes

F22 usa dos redes:

1. `f22_morfologia_seed14.pt`: clasificador morfológico principal.
2. `f20_gate_paced_seed14.pt`: especialista con características de alta
   frecuencia para recuperar Paced.

Los checkpoints no se almacenan en Git. `manifest.json` fija tamaño, SHA-256 y
URL del Release `f22-seed14-v1`.

## Instalación

Desde la raíz del repositorio:

```bash
python -m venv .venv-f22
source .venv-f22/bin/activate
python -m pip install -r contrib/carlos/f22_seed14/requirements.txt
python contrib/carlos/f22_seed14/descargar_modelo.py
python contrib/carlos/f22_seed14/validar_modelo.py
```

El Release debe contener ambos checkpoints con los nombres y hashes declarados
en `manifest.json`. Mientras el Release no haya sido publicado, la descarga
fallará explícitamente sin modificar el repositorio.

## Predicción

Registro WFDB (`.hea` + `.dat`):

```bash
python contrib/carlos/f22_seed14/predecir_ecg.py \
  --entrada data/paciente/registro.hea \
  --inicio 0 \
  --salida prediccion.json
```

Matriz NumPy en mV con forma `[muestras, 12]` o `[12, muestras]`:

```bash
python contrib/carlos/f22_seed14/predecir_ecg.py \
  --entrada ventana.npy --formato npy --fs 500
```

La ventana seleccionada debe contener exactamente 10 segundos. Un registro
WFDB puede tener 9 o 12 derivaciones reconocibles; las ausentes se representan
como cero igual que durante el entrenamiento.

Uso desde Python:

```python
import numpy as np

from contrib.carlos.f22_seed14 import F22Predictor

ecg_mv = np.load("ventana.npy")
predictor = F22Predictor()
resultado = predictor.predict(ecg_mv, sample_rate_hz=500)
print(resultado["class"], resultado["confidence"])
```

La salida incluye la decisión final, la activación del gate, la protección VT
y las probabilidades separadas de ambos especialistas. Consulta
[`model_card.md`](model_card.md) antes de presentar los valores.
