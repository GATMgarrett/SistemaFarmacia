import pandas as pd
import torch
import pyro
import pyro.distributions as dist
from pyro.infer import MCMC, NUTS
import matplotlib.pyplot as plt
from ventas.models import DetalleVenta

# Cargar datos de ventas
detalle_ventas = DetalleVenta.objects.all()
detalle_ventas_data = pd.DataFrame(list(detalle_ventas.values('venta__fecha_venta', 'cantidad')))

# Preprocesar los datos
detalle_ventas_data['fecha_venta'] = pd.to_datetime(detalle_ventas_data['venta__fecha_venta'])
detalle_ventas_data['mes'] = detalle_ventas_data['fecha_venta'].dt.month
detalle_ventas_data['año'] = detalle_ventas_data['fecha_venta'].dt.year

# Crear matriz de entrada (X) y salida (y)
X = detalle_ventas_data[['mes', 'año']].values
y = detalle_ventas_data['cantidad'].values

# Convertir a tensores
X_tensor = torch.tensor(X, dtype=torch.float32)
y_tensor = torch.tensor(y, dtype=torch.float32)

# Modelo bayesiano
def model(X, y=None):
    alpha = pyro.sample("alpha", dist.Normal(0., 10.))
    beta = pyro.sample("beta", dist.Normal(0., 10.).expand([X.shape[1]]))  # Coeficientes para mes y año
    sigma = pyro.sample("sigma", dist.HalfNormal(1.))
    mu = alpha + torch.matmul(X, beta)  # Modelo lineal
    pyro.sample("obs", dist.Normal(mu, sigma), obs=y)
    return mu

# Iniciar inferencia con NUTS
nuts_kernel = NUTS(model, target_accept_prob=0.8)
mcmc = MCMC(nuts_kernel, num_samples=100, warmup_steps=50)
mcmc.run(X_tensor, y_tensor)

# Obtener muestras posteriores
posterior_samples = mcmc.get_samples()
alpha = posterior_samples['alpha']  # [num_samples]
beta = posterior_samples['beta']    # [num_samples, num_features]

# Generar datos para los próximos 6 meses (modificación)
future_dates = pd.date_range(start='2024-12-01', periods=6, freq='MS')  # 6 meses en vez de 12
future_data = pd.DataFrame({'fecha_venta': future_dates})
future_data['mes'] = future_data['fecha_venta'].dt.month
future_data['año'] = future_data['fecha_venta'].dt.year

future_X_tensor = torch.tensor(future_data[['mes', 'año']].values, dtype=torch.float32)

# Ajustar dimensiones para garantizar compatibilidad
alpha_expanded = alpha.unsqueeze(1)  # De [num_samples] a [num_samples, 1]
beta_expanded = beta.unsqueeze(2)    # De [num_samples, num_features] a [num_samples, num_features, 1]

# Predicciones para datos futuros
predictions = alpha_expanded + torch.matmul(future_X_tensor.unsqueeze(0), beta_expanded).squeeze(2)

# Promediar las predicciones
predicted_means = predictions.mean(dim=0).detach().numpy()
predicted_means = predicted_means.clip(min=0)  # Asegurar que las ventas sean >= 0

# Guardar predicciones en el DataFrame
future_data['predicted_sales'] = predicted_means

# Mostrar resultados
print(future_data[['fecha_venta', 'predicted_sales']])

# Graficar predicciones
plt.figure(figsize=(10, 5))
plt.plot(future_data['fecha_venta'], future_data['predicted_sales'], label="Predicción de Ventas Futuras", marker='o')
plt.xlabel("Fecha")
plt.ylabel("Ventas Predichas")
plt.title("Predicción de Ventas Mensuales")
plt.legend()
plt.grid()
plt.show()
