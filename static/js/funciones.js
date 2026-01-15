$(document).ready(function () {
    $('#consultar_egresados').on('click', function () {
        ocultarBienvenida();
        $.ajax({
            url: '/consulta_egresados',
            method: 'GET',
            success: function (data) {
                $('#actualizable').html(data);
            },
            error: function (err) {
                console.log('Error al cargar los alumnos')
            }

        });

    });
});
document.getElementById("btn_registro_egresado").addEventListener("click", function (e) {
    e.preventDefault();
    
    const formElement = document.getElementById("registro_egresado");
    const formData = new FormData(formElement);

    // --- Función de Alerta ---
    const mostrarError = (mensaje, campoId) => {
        Swal.fire({
            icon: 'error',
            title: 'Validación',
            text: mensaje,
            confirmButtonColor: '#3085d6'
        });
        if (campoId) {
            const el = document.getElementById(campoId);
            el.classList.add("is-invalid");
            el.focus();
        }
    };

    // --- Limpiar estados de error previos ---
    document.querySelectorAll(".is-invalid").forEach(el => el.classList.remove("is-invalid"));

    // --- 1. Validaciones de Campos Obligatorios ---
    const nombre = document.getElementById("nombre_egresado").value.trim();
    if (nombre.length < 2) return mostrarError("Ingresa un nombre válido (Ej. Juan).", "nombre_egresado");

    const apPaterno = document.getElementById("apellido_paterno").value.trim();
    if (apPaterno.length < 2) return mostrarError("Ingresa el apellido paterno.", "apellido_paterno");

    // --- 2. Validación de Matrícula ---
    const matricula = document.getElementById("matricula").value.trim();
    if (!/^\d{8}$/.test(matricula)) {
        return mostrarError("La matrícula debe tener exactamente 8 números.", "matricula");
    }

    // --- 3. Validación de Teléfono ---
    const telefono = document.getElementById("telefono").value.trim();
    if (telefono !== "" && !/^\d{10}$/.test(telefono)) {
        return mostrarError("El teléfono debe tener 10 dígitos.", "telefono");
    }

    // --- 4. Validación de Correo ---
    const correo = document.getElementById("coorreo_electronico").value.trim();
    const regexCorreo = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
    if (!regexCorreo.test(correo)) {
        return mostrarError("Ingresa un correo válido.", "coorreo_electronico");
    }

    // --- 5. Validación de Perfil Profesional (AHORA SIEMPRE OBLIGATORIO) ---
    // Se eliminó el "if (estatusLab === 'Empleado')"
    const perfil = document.getElementById("perfil").value.trim();
    if (perfil === "") {
        return mostrarError("Debes especificar tu perfil profesional (Ej. Lic. en Administración).", "perfil");
    }

    // --- 6. Validación de Archivo si es requerido ---
    const grupoArchivo = document.getElementById("grupo_archivo_modalidad");
    if (window.getComputedStyle(grupoArchivo).display !== "none") {
        const archivo = document.getElementById("archivo_modalidad");
        if (archivo.files.length === 0) return mostrarError("Debes subir el PDF de acreditación.", "archivo_modalidad");
    }

    const password = document.getElementById("password").value;
    if (password.length < 6) return mostrarError("La contraseña debe tener al menos 6 caracteres.", "password");

    const carrera = document.getElementById("id_carrera").value;
    if (carrera === "") return mostrarError("Selecciona una carrera.", "id_carrera");

    // --- 7. Envío de Datos ---
    fetch("/registrar_egresado", {
        method: "POST",
        body: formData
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            Swal.fire({
                icon: 'success',
                title: '¡Registrado!',
                text: 'Egresado guardado correctamente.',
                timer: 2000,
                showConfirmButton: false
            }).then(() => {
                formElement.reset();
                document.getElementById("previewegr").src = "/static/images/user.png";
                const modalElement = document.getElementById("modalregistroegresado");
                const modal = bootstrap.Modal.getInstance(modalElement);
                if (modal) modal.hide();
                
                const btnConsulta = document.getElementById("consultar_egresados");
                if (btnConsulta) btnConsulta.click();
            });
        } else {
            Swal.fire('Error de Registro', data.message, 'error');
        }
    })
    .catch(error => {
        console.error(error);
        Swal.fire('Error crítico', 'No se pudo conectar con el servidor', 'error');
    });
});
/* ===========================
   FUNCIONES GRÁFICA
=========================== */
let grafica;

function cargarCarreras() {

    fetch("/lista_carreras")
        .then(r => r.json())
        .then(data => {

            const select = $("#filtro_carrera");
            select.html('<option value="">Todas</option>');

            data.forEach(c => {
                select.append(
                    `<option value="${c.id_carrera}">${c.nombre_carrera}</option>`
                );
            });
        });
}

function cargarGrafica() {

    const estatus = $("#filtro_estatus").val();
    const carrera = $("#filtro_carrera").val();

    fetch(`/datos_estadisticas?estatus=${estatus}&carrera=${carrera}`)
        .then(r => r.json())
        .then(data => {

            const labels = [];
            const valores = [];
            const colores = [];

            let total = 0;
            let resumenHTML = "";
            let leyendaHTML = "";

            data.forEach(d => {

                labels.push(d.estatus_titulacion);
                valores.push(d.total);
                total += d.total;

                let color = "#6c757d";
                switch (d.estatus_titulacion.toLowerCase()) {
                    case "titulado":
                        color = "#198754";
                        break;
                    case "no titulado":
                        color = "#dc3545";
                        break;
                    case "en proceso":
                        color = "#ffc107";
                        break;
                }

                colores.push(color);

                // 🔹 LEYENDA
                leyendaHTML += `
                    <div class="mb-2 d-flex align-items-center">
                        <div style="width:15px;height:15px;background:${color};border-radius:3px;margin-right:8px;"></div>
                        <strong>${d.total}</strong>
                        <span class="ms-2">${d.estatus_titulacion}</span>
                    </div>
                `;

                // 🔹 TARJETAS
                resumenHTML += `
                    <div class="col-md-3 mb-3">
                        <div class="card text-center shadow-sm">
                            <div class="card-body">
                                <small class="text-muted">${d.estatus_titulacion}</small>
                                <h3 style="color:${color}">${d.total}</h3>
                                <small class="text-muted">egresados</small>
                            </div>
                        </div>
                    </div>
                `;
            });
    // 🔹 TOTAL (solo cuando está seleccionado "Todos")
    if (estatus === "") {
        resumenHTML += `
            <div class="col-md-4 mb-3">
                <div class="card text-center shadow border-success">
                    <div class="card-body">
                        <small class="text-muted">Total</small>
                        <h2 class="text-success">${total}</h2>
                        <small class="text-muted">egresados</small>
                    </div>
                </div>
            </div>
        `;
    }


            $("#resumenEgresados").html(resumenHTML);

            if (grafica) grafica.destroy();

            grafica = new Chart(document.getElementById("graficaEgresados"), {
                type: "bar",
                data: {
                    labels: labels,
                    datasets: [{
                        data: valores,
                        backgroundColor: colores
                    }]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    plugins: {
                        legend: { display: false }
                    },
                    scales: {
                        y: { beginAtZero: true }
                    }
                }
            });
        });
}

$(document).on("click", "#ver_estadisticas", function () {
    ocultarPanel(); // Oculta el dashboard de bienvenida
    ocultarBienvenida(); // Por si acaso

    // 1. Cargamos el contenedor de las estadísticas en el área actualizable
    // Nota: Aquí asumo que tienes una ruta en Flask que devuelve solo el HTML de las estadísticas
    $.ajax({
        url: '/vista_estadisticas', // Crea esta ruta en Flask si no la tienes
        method: 'GET',
        success: function (html) {
            $('#actualizable').html(html);

            // 2. Una vez que el HTML existe en el DOM, inicializamos todo
            cargarCarreras(); // Llena el select de carreras
            cargarGrafica();  // Dibuja la gráfica por primera vez
        },
        error: function () {
            console.log("Error al cargar la vista de reportes");
        }
    });

    // Manejo de clases active en el menú
    $(".menu li").removeClass("active");
    $(this).addClass("active");
});


/* ===========================
   EVENTOS DE FILTROS
=========================== */
$(document).on("change", "#filtro_estatus, #filtro_carrera", function () {
    cargarGrafica();
});
/* ===========================
   menu administrador
=========================== */
let vistaInicio = "";

document.addEventListener("DOMContentLoaded", () => {
    vistaInicio = document.getElementById("actualizable").innerHTML;
});

document.addEventListener("DOMContentLoaded", () => {
    const dashboard = document.querySelector(".dashboard");
    const toggleBtn = document.getElementById("toggleMenu");
    const overlay = document.getElementById("overlay");

    // Abrir / cerrar menú
    toggleBtn.addEventListener("click", (e) => {
        e.stopPropagation();
        dashboard.classList.toggle("collapsed");
    });

    // Cerrar al hacer click fuera
    overlay.addEventListener("click", () => {
        dashboard.classList.add("collapsed");
    });

    // Cerrar al seleccionar opción del menú
document.querySelectorAll(".menu li:not(.logout)").forEach(item => {
    item.addEventListener("click", () => {
        dashboard.classList.add("collapsed");
    });
});
});
$(document).on("click", "#logoutBtn", function (e) {
    e.preventDefault();

    // Cerramos el sidebar si está abierto (para mejor UX)
    const dashboard = document.querySelector(".dashboard");
    dashboard.classList.add("collapsed");

    Swal.fire({
        title: '¿Cerrar sesión?',
        text: "Tendrás que ingresar tus credenciales nuevamente para acceder.",
        icon: 'warning',
        showCancelButton: true,
        confirmButtonColor: '#dc3545', // Color rojo (danger)
        cancelButtonColor: '#6c757d',  // Color gris (secondary)
        confirmButtonText: '<i class="bi bi-box-arrow-right"></i> Sí, salir',
        cancelButtonText: 'Cancelar',
        reverseButtons: true // Pone el botón de cancelar a la izquierda
    }).then((result) => {
        if (result.isConfirmed) {
            // Mostramos una alerta de "Cerrando..." antes de redireccionar
            Swal.fire({
                title: 'Adiós',
                text: 'Cerrando sesión de forma segura...',
                icon: 'success',
                timer: 1000,
                showConfirmButton: false
            }).then(() => {
                // Redirección al endpoint de Flask
                window.location.href = "/logout";
            });
        }
    });
});
// Cuando se cierra el modal de logout
document
  .getElementById("logoutModal")
  .addEventListener("hidden.bs.modal", function () {

      // Cerrar sidebar si está abierto
      const dashboard = document.querySelector(".dashboard");
      dashboard.classList.add("collapsed");

      // Ocultar overlay manualmente
      const overlay = document.getElementById("overlay");
      if (overlay) {
          overlay.style.display = "none";
      }
});
function mostrarToast(mensaje) {
    const toastEl = document.getElementById("toastMensaje");
    const toastTexto = document.getElementById("toastTexto");

    toastTexto.textContent = mensaje;

    const toast = new bootstrap.Toast(toastEl);
    toast.show();
}





$(document).on("click", "#panel_control", function () {
    $("#actualizable").html(vistaInicio);
    $("#welcomeAdmin").show(); // 👈 IMPORTANTE

    $(".menu li").removeClass("active");
    $(this).addClass("active");
});

function ocultarBienvenida() {
    const welcome = document.getElementById("welcomeAdmin");
    if (welcome) {
        welcome.style.display = "none";
    }
}
function mostrarPanel() {
    document.getElementById("panelDashboard").style.display = "block";
    document.getElementById("actualizable").style.display = "none";
}

function ocultarPanel() {
    document.getElementById("panelDashboard").style.display = "none";
    document.getElementById("actualizable").style.display = "block";
}
document.getElementById("panel_control").addEventListener("click", () => {
    mostrarPanel();
});

document.getElementById("consultar_egresados").addEventListener("click", () => {
    ocultarPanel();
});

document.getElementById("ver_estadisticas").addEventListener("click", () => {
    ocultarPanel();
});


//Tala responsiva en celular



