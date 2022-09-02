from django.core.checks import messages
from django.shortcuts import render, HttpResponse, get_object_or_404, redirect
from . models import Device, Log
import paramiko
from datetime import datetime
import time

def home(request):
    all_device = Device.objects.all()
    cisco_device = Device.objects.filter(vendor='cisco')
    mikrotik_device = Device.objects.filter(vendor='mikrotik')
    last_event = Log.objects.all().order_by('-id')[:5]

    context = {
        'all_device': len(all_device),
        'cisco_device': len(cisco_device),
        'mikrotik_device': len(mikrotik_device),
        'last_event': last_event
    }

    return render(request, 'home.html', context)

def devices(request):
    all_device = Device.objects.all()

    context = {
        'all_device': all_device
    }

    return render(request, 'devices.html', context)

def configure(request):
    if request.method == "POST":
        selected_device_id = request.POST.getlist('device')
        mikrotik_command = request.POST['mikrotik_command'].splitlines()
        cisco_command = request.POST['cisco_command'].splitlines()
        for x in selected_device_id:
            try:
                dev = get_object_or_404(Device, pk=x)
                ssh_client = paramiko.SSHClient()
                ssh_client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
                ssh_client.connect(hostname=dev.ip_address, username=dev.username, password= dev.password,look_for_keys=False,allow_agent=False)
                
                if dev.vendor.lower() == 'cisco':
                    conn = ssh_client.invoke_shell()
                    conn.send("configure terminal\n")
                    for cmd in cisco_command:
                        conn.send(cmd + "\n")
                        time.sleep(1)
                else:
                    for cmd in mikrotik_command:
                        ssh_client.exec_command(cmd)
                log = Log(target=dev.ip_address, action="Configure", status="Success", time = datetime.utcnow(), messages="No Error")
                log.save()         
            except Exception as e:
                log = Log(target=dev.ip_address, action="Configure", status="Error", time = datetime.utcnow(), messages=e)
                log.save()

        return redirect('home')

    #GET METHOD    
    else:
        devices = Device.objects.all()
        context = {
            'devices': devices,
            'mode': 'Configure'
        }
        return render(request, 'config.html', context)    

def verify_config(request):
    if request.method == 'POST':
        result = []
        selected_device_id = request.POST.getlist('device')
        mikrotik_command = request.POST['mikrotik_command'].splitlines()
        cisco_command = request.POST['cisco_command'].splitlines()
        for x in selected_device_id:
            try:
                dev = get_object_or_404(Device, pk=x)
                ssh_client = paramiko.SSHClient()
                ssh_client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
                ssh_client.connect(hostname=dev.ip_address, username=dev.username, password=dev.password,look_for_keys=False,allow_agent=False)

                if dev.vendor.lower() == 'mikrotik':
                    for cmd in mikrotik_command:
                        stdin, stdout, stderr = ssh_client.exec_command(cmd)
                        result.append("Result on {}".format(dev.ip_address))
                        result.append(stdout.read().decode())
                    else:
                        conn = ssh_client.invoke_shell()
                        conn.send('enable\n')
                        conn.send('admin\n')
                        conn.send('terminal length 0\n')
                        for cmd in cisco_command:
                            result.append("Result on {}".format(dev.ip_address))
                            conn.send(cmd + "\n")
                            time.sleep(1)
                            output = conn.recv(65535)
                            result.append(output.decode())
                    log = Log(target=dev.ip_address, action="Verify Config", status="Success", time = datetime.utcnow(), messages = "No Error")
                    log.save()         
            except Exception as e:
                    log = Log(target=dev.ip_address, action="Verify Config", status="Error", time = datetime.utcnow(), messages = e)
                    log.save()    
        result = '\n'.join(result)
        return render(request, 'verify_result.html', {'result': result})

    else:
        devices = Device.objects.all()
        context = {
            'devices': devices,
            'mode': 'Verify Configures'
        }
        return render(request, 'config.html', context)

def log(request):
    logs = Log.objects.all()

    context = {
        'Logs': logs
    }  

    return render(request, 'log.html', context)                     
